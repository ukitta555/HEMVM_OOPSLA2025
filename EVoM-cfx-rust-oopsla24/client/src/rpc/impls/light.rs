// Copyright 2019 Conflux Foundation. All rights reserved.
// Conflux is free software and distributed under GNU General Public License.
// See http://www.gnu.org/licenses/

use cfx_types::{
    AddressSpaceUtil, BigEndianHash, Space, H160, H256, H520, U128, U256, U64,
};
use cfxcore::{
    block_data_manager::BlockDataManager,
    light_protocol::{
        self, query_service::TxInfo, Error as LightError, ErrorKind,
    },
    rpc_errors::{account_result_to_rpc_result, invalid_params_check},
    verification::EpochReceiptProof,
    ConsensusGraph, LightQueryService, PeerInfo, SharedConsensusGraph,
};
use cfxcore_accounts::AccountProvider;
use delegate::delegate;
use diem_types::transaction::TransactionPayload;
use futures::future::{self, FutureExt, TryFutureExt};
use jsonrpc_core::{BoxFuture, Error as RpcError, Result as JsonRpcResult};
use network::{
    node_table::{Node, NodeId},
    throttling, SessionDetails, UpdateNodeOperation,
};
use primitives::{
    Account, DepositInfo, StorageRoot, TransactionWithSignature, VoteStakeInfo,
};
use rlp::Encodable;
use std::{collections::BTreeMap, net::SocketAddr, sync::Arc};
// To convert from RpcResult to BoxFuture by delegate! macro automatically.
use crate::{
    common::delegate_convert,
    rpc::{
        error_codes,
        impls::common::{self, RpcImpl as CommonImpl},
        traits::{cfx::Cfx, debug::LocalRpc, test::TestRpc},
        types::{
            errors::check_rpc_address_network,
            pos::{Block as PosBlock, PoSEpochReward},
            Account as RpcAccount, AccountPendingInfo,
            AccountPendingTransactions, BlameInfo, Block as RpcBlock,
            BlockHashOrEpochNumber, Bytes, CallRequest, CfxRpcLogFilter,
            CheckBalanceAgainstTransactionResponse, ConsensusGraphStates,
            EpochNumber, EstimateGasAndCollateralResponse, Log as RpcLog,
            PoSEconomics, Receipt as RpcReceipt, RewardInfo as RpcRewardInfo,
            RpcAddress, SendTxRequest, SponsorInfo, Status as RpcStatus,
            StorageCollateralInfo, SyncGraphStates, TokenSupplyInfo,
            Transaction as RpcTransaction, VoteParamsInfo, WrapTransaction,
        },
        RpcBoxFuture, RpcResult,
    },
};
use cfx_addr::Network;
use cfx_parameters::rpc::GAS_PRICE_DEFAULT_VALUE;
use cfxcore::{
    light_protocol::QueryService, rpc_errors::ErrorKind::LightProtocol,
};
use diem_types::account_address::AccountAddress;

// macro for reducing boilerplate for unsupported methods
macro_rules! not_supported {
    () => {};
    ( fn $fn:ident ( &self $(, $name:ident : $type:ty)* ) $( -> BoxFuture<$ret:ty> )? ; $($tail:tt)* ) => {
        #[allow(unused_variables)]
        fn $fn ( &self $(, $name : $type)* ) $( -> BoxFuture<$ret> )? {
            use jsonrpc_core::futures::future::{Future, IntoFuture};
            Err(error_codes::unimplemented(Some("Tracking issue: https://github.com/Conflux-Chain/conflux-rust/issues/1461".to_string())))
                .into_future()
                .boxed()
        }

        not_supported!($($tail)*);
    };
    ( fn $fn:ident ( &self $(, $name:ident : $type:ty)* ) $( -> $ret:ty )? ; $($tail:tt)* ) => {
        #[allow(unused_variables)]
        fn $fn ( &self $(, $name : $type)* ) $( -> $ret )? {
            Err(error_codes::unimplemented(Some("Tracking issue: https://github.com/Conflux-Chain/conflux-rust/issues/1461".to_string())))
        }

        not_supported!($($tail)*);
    };
}

pub struct RpcImpl {
    // account provider used for signing transactions
    accounts: Arc<AccountProvider>,

    // consensus graph
    consensus: SharedConsensusGraph,

    // block data manager
    data_man: Arc<BlockDataManager>,

    // helper API for retrieving verified information from peers
    light: Arc<LightQueryService>,
}

impl RpcImpl {
    pub fn new(
        light: Arc<LightQueryService>, accounts: Arc<AccountProvider>,
        consensus: SharedConsensusGraph, data_man: Arc<BlockDataManager>,
    ) -> Self
    {
        RpcImpl {
            accounts,
            consensus,
            data_man,
            light,
        }
    }

    fn load_test(&self) -> RpcResult<U256> {
        Ok(U256::from(1))
    }

    fn check_address_network(
        network: Network, light: &QueryService,
    ) -> RpcResult<()> {
        invalid_params_check(
            "address",
            check_rpc_address_network(Some(network), light.get_network_type()),
        )
    }

    fn get_epoch_number_with_pivot_check(
        consensus_graph: SharedConsensusGraph,
        block_hash_or_epoch_number: Option<BlockHashOrEpochNumber>,
    ) -> RpcResult<EpochNumber>
    {
        match block_hash_or_epoch_number {
            Some(BlockHashOrEpochNumber::BlockHashWithOption {
                hash,
                require_pivot,
            }) => {
                let epoch_number = consensus_graph
                    .as_any()
                    .downcast_ref::<ConsensusGraph>()
                    .expect("downcast should succeed")
                    .get_block_epoch_number_with_pivot_check(
                        &hash,
                        require_pivot.unwrap_or(true),
                    )?;
                Ok(EpochNumber::Num(U64::from(epoch_number)))
            }
            Some(BlockHashOrEpochNumber::EpochNumber(epoch_number)) => {
                Ok(epoch_number)
            }
            None => Ok(EpochNumber::LatestState),
        }
    }

    fn account(
        &self, address: RpcAddress, num: Option<EpochNumber>,
    ) -> RpcBoxFuture<RpcAccount> {
        let epoch = num.unwrap_or(EpochNumber::LatestState).into();

        info!(
            "RPC Request: cfx_getAccount address={:?} epoch={:?}",
            address, epoch
        );

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            Self::check_address_network(address.network, &light)?;
            let network = address.network;

            let account = invalid_params_check(
                "epoch",
                light.get_account(epoch, address.hex_address).await,
            )?;

            let account = account.unwrap_or(account_result_to_rpc_result(
                "address",
                Ok(Account::new_empty_with_balance(
                    &address.hex_address.with_native_space(),
                    &U256::zero(), /* balance */
                    &U256::zero(), /* nonce */
                )),
            )?);

            Ok(RpcAccount::try_from(account, network)?)
        };

        Box::new(fut.boxed().compat())
    }

    fn balance(
        &self, address: RpcAddress,
        block_hash_or_epoch_number: Option<BlockHashOrEpochNumber>,
    ) -> RpcBoxFuture<U256>
    {
        info!(
            "RPC Request: cfx_getBalance address={:?} epoch={:?}",
            address,
            block_hash_or_epoch_number
                .as_ref()
                .ok_or(EpochNumber::LatestState)
        );

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();
        let consensus_graph = self.consensus.clone();

        let fut = async move {
            let epoch = Self::get_epoch_number_with_pivot_check(
                consensus_graph,
                block_hash_or_epoch_number,
            )?
            .into();
            Self::check_address_network(address.network, &light)?;

            let account = invalid_params_check(
                "address",
                light.get_account(epoch, address.into()).await,
            )?;

            Ok(account
                .map(|account| account.balance.into())
                .unwrap_or_default())
        };

        Box::new(fut.boxed().compat())
    }

    fn admin(
        &self, address: RpcAddress, num: Option<EpochNumber>,
    ) -> RpcBoxFuture<Option<RpcAddress>> {
        let epoch = num.unwrap_or(EpochNumber::LatestState).into();
        let network = address.network;

        info!(
            "RPC Request: cfx_getAdmin address={:?} epoch={:?}",
            address, epoch
        );

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            Self::check_address_network(address.network, &light)?;

            let account = invalid_params_check(
                "address",
                light.get_account(epoch, address.into()).await,
            )?;

            match account {
                None => Ok(None),
                Some(acc) => {
                    Ok(Some(RpcAddress::try_from_h160(acc.admin, network)?))
                }
            }
        };

        Box::new(fut.boxed().compat())
    }

    fn sponsor_info(
        &self, address: RpcAddress, num: Option<EpochNumber>,
    ) -> RpcBoxFuture<SponsorInfo> {
        let epoch = num.unwrap_or(EpochNumber::LatestState).into();

        info!(
            "RPC Request: cfx_getSponsorInfo address={:?} epoch={:?}",
            address, epoch
        );

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            Self::check_address_network(address.network, &light)?;
            let network = address.network;

            let account = invalid_params_check(
                "address",
                light.get_account(epoch, address.into()).await,
            )?;

            match account {
                None => Ok(SponsorInfo::default(network)?),
                Some(acc) => {
                    Ok(SponsorInfo::try_from(acc.sponsor_info, network)?)
                }
            }
        };

        Box::new(fut.boxed().compat())
    }

    fn staking_balance(
        &self, address: RpcAddress, num: Option<EpochNumber>,
    ) -> RpcBoxFuture<U256> {
        let epoch = num.unwrap_or(EpochNumber::LatestState).into();

        info!(
            "RPC Request: cfx_getStakingBalance address={:?} epoch={:?}",
            address, epoch
        );

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            Self::check_address_network(address.network, &light)?;

            let account = invalid_params_check(
                "address",
                light.get_account(epoch, address.into()).await,
            )?;

            Ok(account
                .map(|account| account.staking_balance.into())
                .unwrap_or_default())
        };

        Box::new(fut.boxed().compat())
    }

    fn deposit_list(
        &self, address: RpcAddress, num: Option<EpochNumber>,
    ) -> RpcBoxFuture<Vec<DepositInfo>> {
        let epoch = num.unwrap_or(EpochNumber::LatestState).into();

        info!(
            "RPC Request: cfx_getDepositList address={:?} epoch_num={:?}",
            address, epoch
        );

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            Self::check_address_network(address.network, &light)?;

            let maybe_list = invalid_params_check(
                "address",
                light.get_deposit_list(epoch, address.into()).await,
            )?;

            match maybe_list {
                None => Ok(vec![]),
                Some(deposit_list) => Ok(deposit_list.0),
            }
        };

        Box::new(fut.boxed().compat())
    }

    pub fn account_pending_info(
        &self, address: RpcAddress,
    ) -> RpcBoxFuture<Option<AccountPendingInfo>> {
        info!("RPC Request: cfx_getAccountPendingInfo({:?})", address);

        let fut = async move {
            // TODO impl light node rpc
            Ok(None)
        };
        Box::new(fut.boxed().compat())
    }

    fn vote_list(
        &self, address: RpcAddress, num: Option<EpochNumber>,
    ) -> RpcBoxFuture<Vec<VoteStakeInfo>> {
        let epoch = num.unwrap_or(EpochNumber::LatestState).into();

        info!(
            "RPC Request: cfx_getVoteList address={:?} epoch_num={:?}",
            address, epoch
        );

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            Self::check_address_network(address.network, &light)?;

            let maybe_list = invalid_params_check(
                "address",
                light.get_vote_list(epoch, address.into()).await,
            )?;

            match maybe_list {
                None => Ok(vec![]),
                Some(vote_list) => Ok(vote_list.0),
            }
        };

        Box::new(fut.boxed().compat())
    }

    fn collateral_for_storage(
        &self, address: RpcAddress, num: Option<EpochNumber>,
    ) -> RpcBoxFuture<U256> {
        let epoch = num.unwrap_or(EpochNumber::LatestState).into();

        info!(
            "RPC Request: cfx_getCollateralForStorage address={:?} epoch={:?}",
            address, epoch
        );

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            Self::check_address_network(address.network, &light)?;

            let account = invalid_params_check(
                "address",
                light.get_account(epoch, address.into()).await,
            )?;

            Ok(account
                .map(|account| account.collateral_for_storage.into())
                .unwrap_or_default())
        };

        Box::new(fut.boxed().compat())
    }

    fn code(
        &self, address: RpcAddress,
        block_hash_or_epoch_number: Option<BlockHashOrEpochNumber>,
    ) -> RpcBoxFuture<Bytes>
    {
        info!(
            "RPC Request: cfx_getCode address={:?} epoch={:?}",
            address,
            block_hash_or_epoch_number
                .as_ref()
                .ok_or(EpochNumber::LatestState)
        );

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();
        let consensus_graph = self.consensus.clone();

        let fut = async move {
            let epoch = Self::get_epoch_number_with_pivot_check(
                consensus_graph,
                block_hash_or_epoch_number,
            )?
            .into();
            Self::check_address_network(address.network, &light)?;

            // FIMXE:
            //  We should get rid of the invalid_params_check when the
            //  error conversion is done within the light service methods.
            //  Same for all other usages here in this file.
            Ok(Bytes::new(
                invalid_params_check(
                    "address",
                    light.get_code(epoch, address.into()).await,
                )?
                .unwrap_or_default(),
            ))
        };

        Box::new(fut.boxed().compat())
    }

    fn get_logs(&self, filter: CfxRpcLogFilter) -> RpcBoxFuture<Vec<RpcLog>> {
        info!("RPC Request: cfx_getLogs filter={:?}", filter);

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            // all addresses specified should be for the correct network
            if let Some(addresses) = &filter.address {
                for address in addresses.iter() {
                    invalid_params_check(
                        "filter.address",
                        check_rpc_address_network(
                            Some(address.network),
                            light.get_network_type(),
                        ),
                    )?;
                }
            }

            let filter = filter.into_primitive()?;

            let logs = light
                .get_logs(filter)
                .await
                .map_err(|e| e.to_string()) // TODO(thegaram): return meaningful error
                .map_err(RpcError::invalid_params)?;

            Ok(logs
                .into_iter()
                .map(|l| {
                    RpcLog::try_from_localized(l, *light.get_network_type())
                })
                .collect::<Result<_, _>>()?)
        };

        Box::new(fut.boxed().compat())
    }

    fn send_tx_helper(
        light: Arc<LightQueryService>, raw: Bytes,
    ) -> RpcResult<H256> {
        let raw: Vec<u8> = raw.into_vec();

        // decode tx so that we have its hash
        // this way we also avoid spamming peers with invalid txs
        let tx: TransactionWithSignature = rlp::decode(&raw.clone())
            .map_err(|e| format!("Failed to decode tx: {:?}", e))
            .map_err(RpcError::invalid_params)?;

        debug!("Deserialized tx: {:?}", tx);

        // TODO(thegaram): consider adding a light node specific tx pool;
        // light nodes would track those txs and maintain their statuses
        // for future queries

        match /* success = */ light.send_raw_tx(raw) {
            true => Ok(tx.hash().into()),
            false => bail!(LightProtocol(light_protocol::ErrorKind::InternalError("Unable to relay tx".into()).into())),
        }
    }

    fn send_raw_transaction(&self, raw: Bytes) -> RpcResult<H256> {
        info!("RPC Request: cfx_sendRawTransaction bytes={:?}", raw);
        Self::send_tx_helper(self.light.clone(), raw)
    }

    fn send_transaction(
        &self, mut tx: SendTxRequest, password: Option<String>,
    ) -> RpcBoxFuture<H256> {
        info!("RPC Request: cfx_sendTransaction tx={:?}", tx);

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();
        let accounts = self.accounts.clone();

        let fut = async move {
            tx.check_rpc_address_network("tx", light.get_network_type())?;

            if tx.nonce.is_none() {
                // TODO(thegaram): consider adding a light node specific tx pool
                // to track the nonce

                let address = tx.from.clone().into();
                let epoch = EpochNumber::LatestState.into_primitive();

                let nonce = light
                    .get_account(epoch, address)
                    .await?
                    .map(|a| a.nonce)
                    .unwrap_or(U256::zero());

                tx.nonce.replace(nonce.into());
                debug!("after loading nonce in latest state, tx = {:?}", tx);
            }

            let epoch_height = light.get_latest_verifiable_epoch_number().map_err(|_| {
               format!("the light client cannot retrieve/verify the latest mined pivot block.")
            })?;
            let chain_id = light.get_latest_verifiable_chain_id().map_err(|_| {
                format!("the light client cannot retrieve/verify the latest chain_id.")
            })?;
            let tx = tx.sign_with(
                epoch_height,
                chain_id.in_native_space(),
                password,
                accounts,
            )?;

            Self::send_tx_helper(light, Bytes::new(tx.rlp_bytes()))
        };

        Box::new(fut.boxed().compat())
    }

    fn storage_root(
        &self, address: RpcAddress, epoch_num: Option<EpochNumber>,
    ) -> RpcBoxFuture<Option<StorageRoot>> {
        let epoch_num = epoch_num.unwrap_or(EpochNumber::LatestState);

        info!(
            "RPC Request: cfx_getStorageRoot address={:?} epoch={:?})",
            address, epoch_num
        );

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            Self::check_address_network(address.network, &light)?;

            let root = invalid_params_check(
                "address",
                light
                    .get_storage_root(epoch_num.into(), address.into())
                    .await,
            )?;

            Ok(Some(root))
        };

        Box::new(fut.boxed().compat())
    }

    fn storage_at(
        &self, address: RpcAddress, position: U256,
        block_hash_or_epoch_number: Option<BlockHashOrEpochNumber>,
    ) -> RpcBoxFuture<Option<H256>>
    {
        let position: H256 = H256::from_uint(&position);
        // let epoch_num = epoch_num.unwrap_or(EpochNumber::LatestState);

        info!(
            "RPC Request: cfx_getStorageAt address={:?} position={:?} epoch={:?})",
            address,
            position,
            block_hash_or_epoch_number
                .as_ref()
                .ok_or(EpochNumber::LatestState)
        );

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();
        let consensus_graph = self.consensus.clone();

        let fut = async move {
            let epoch_num = Self::get_epoch_number_with_pivot_check(
                consensus_graph,
                block_hash_or_epoch_number,
            )?;
            Self::check_address_network(address.network, &light)?;

            let maybe_entry = light
                .get_storage(epoch_num.into(), address.into(), position)
                .await
                .map_err(|e| e.to_string()) // TODO(thegaram): return meaningful error
                .map_err(RpcError::invalid_params)?;

            Ok(maybe_entry.map(Into::into))
        };

        Box::new(fut.boxed().compat())
    }

    fn transaction_by_hash(
        &self, hash: H256,
    ) -> RpcBoxFuture<Option<RpcTransaction>> {
        info!("RPC Request: cfx_getTransactionByHash hash={:?}", hash);

        // TODO(thegaram): try to retrieve from local tx pool or cache first

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            let tx = light
                .get_tx(hash.into())
                .await
                .map_err(|e| e.to_string()) // TODO(thegaram): return meaningful error
                .map_err(RpcError::invalid_params)?;

            Ok(Some(RpcTransaction::from_signed(
                &tx,
                None,
                *light.get_network_type(),
            )?))
        };

        Box::new(fut.boxed().compat())
    }

    fn transaction_receipt(
        &self, tx_hash: H256,
    ) -> RpcBoxFuture<Option<RpcReceipt>> {
        let hash: H256 = tx_hash.into();
        info!("RPC Request: cfx_getTransactionReceipt hash={:?}", hash);

        // clone `self.light` to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            // TODO:
            //  return an RpcReceipt directly after splitting cfxcore into
            //  smaller crates. It's impossible now because of circular
            //  dependency.

            // return `null` on timeout
            let tx_info = match light.get_tx_info(hash).await {
                Ok(t) => t,
                Err(LightError(ErrorKind::Timeout(_), _)) => return Ok(None),
                Err(LightError(e, _)) => {
                    bail!(RpcError::invalid_params(e.to_string()))
                }
            };

            let TxInfo {
                tx,
                maybe_block_number,
                receipt,
                tx_index,
                maybe_epoch,
                maybe_state_root,
                prior_gas_used,
            } = tx_info;

            if maybe_block_number.is_none() || tx_index.is_phantom {
                return Ok(None);
            }

            let receipt = RpcReceipt::new(
                tx,
                receipt,
                tx_index,
                prior_gas_used,
                maybe_epoch,
                maybe_block_number.unwrap(),
                maybe_state_root,
                // Can not offer error_message from light node.
                None,
                *light.get_network_type(),
                false,
                false,
            )?;

            Ok(Some(receipt))
        };

        Box::new(fut.boxed().compat())
    }

    pub fn epoch_number(&self, epoch: Option<EpochNumber>) -> RpcResult<U256> {
        let epoch = epoch.unwrap_or(EpochNumber::LatestMined);
        info!("RPC Request: cfx_epochNumber epoch={:?}", epoch);

        invalid_params_check(
            "epoch",
            self.light
                .get_height_from_epoch_number(epoch.into())
                .map(|height| height.into()),
        )
    }

    pub fn next_nonce(
        &self, address: RpcAddress, num: Option<BlockHashOrEpochNumber>,
    ) -> RpcBoxFuture<U256> {
        info!(
            "RPC Request: cfx_getNextNonce address={:?} num={:?}",
            address, num
        );

        // clone to avoid lifetime issues due to capturing `self`
        let consensus_graph = self.consensus.clone();
        let light = self.light.clone();

        let fut = async move {
            Self::check_address_network(address.network, &light)?;

            let epoch =
                Self::get_epoch_number_with_pivot_check(consensus_graph, num)?
                    .into();

            let account = invalid_params_check(
                "address",
                light.get_account(epoch, address.into()).await,
            )?;

            Ok(account
                .map(|account| account.nonce.into())
                .unwrap_or_default())
        };

        Box::new(fut.boxed().compat())
    }

    pub fn block_by_hash(
        &self, hash: H256, include_txs: bool,
    ) -> RpcBoxFuture<Option<RpcBlock>> {
        let hash = hash.into();

        info!(
            "RPC Request: cfx_getBlockByHash hash={:?} include_txs={:?}",
            hash, include_txs
        );

        // clone to avoid lifetime issues due to capturing `self`
        let consensus_graph = self.consensus.clone();
        let data_man = self.data_man.clone();
        let light = self.light.clone();

        let fut = async move {
            let block = match light.retrieve_block(hash).await? {
                None => return Ok(None),
                Some(b) => b,
            };

            let inner = consensus_graph
                .as_any()
                .downcast_ref::<ConsensusGraph>()
                .expect("downcast should succeed")
                .inner
                .read();

            Ok(Some(RpcBlock::new(
                &block,
                *light.get_network_type(),
                &*consensus_graph,
                &*inner,
                &data_man,
                include_txs,
                Some(Space::Native),
            )?))
        };

        Box::new(fut.boxed().compat())
    }

    pub fn block_by_hash_with_pivot_assumption(
        &self, block_hash: H256, pivot_hash: H256, epoch_number: U64,
    ) -> RpcBoxFuture<RpcBlock> {
        let block_hash = block_hash.into();
        let pivot_hash = pivot_hash.into();
        let epoch_number = epoch_number.as_u64();

        info!(
            "RPC Request: cfx_getBlockByHashWithPivotAssumption block_hash={:?} pivot_hash={:?} epoch_number={:?}",
            block_hash, pivot_hash, epoch_number
        );

        // clone to avoid lifetime issues due to capturing `self`
        let consensus_graph = self.consensus.clone();
        let data_man = self.data_man.clone();
        let light = self.light.clone();

        let fut = async move {
            // check pivot assumption
            // make sure not to hold the lock through await's
            consensus_graph
                .as_any()
                .downcast_ref::<ConsensusGraph>()
                .expect("downcast should succeed")
                .inner
                .read()
                .check_block_pivot_assumption(&pivot_hash, epoch_number)
                .map_err(RpcError::invalid_params)?;

            // retrieve block body
            let block = light
                .retrieve_block(block_hash)
                .await?
                .ok_or_else(|| RpcError::invalid_params("Block not found"))?;

            let inner = consensus_graph
                .as_any()
                .downcast_ref::<ConsensusGraph>()
                .expect("downcast should succeed")
                .inner
                .read();

            Ok(RpcBlock::new(
                &block,
                *light.get_network_type(),
                &*consensus_graph,
                &*inner,
                &data_man,
                true,
                Some(Space::Native),
            )?)
        };

        Box::new(fut.boxed().compat())
    }

    pub fn block_by_epoch_number(
        &self, epoch: EpochNumber, include_txs: bool,
    ) -> RpcBoxFuture<Option<RpcBlock>> {
        info!(
            "RPC Request: cfx_getBlockByEpochNumber epoch={:?} include_txs={:?}",
            epoch, include_txs
        );

        // clone to avoid lifetime issues due to capturing `self`
        let consensus_graph = self.consensus.clone();
        let data_man = self.data_man.clone();
        let light = self.light.clone();

        let fut = async move {
            let epoch: u64 = light
                .get_height_from_epoch_number(epoch.into())
                .map_err(|e| e.to_string())
                .map_err(RpcError::invalid_params)?;

            // make sure not to hold the lock through await's
            let hash = consensus_graph
                .as_any()
                .downcast_ref::<ConsensusGraph>()
                .expect("downcast should succeed")
                .inner
                .read()
                .get_pivot_hash_from_epoch_number(epoch)
                .map_err(RpcError::invalid_params)?;

            // retrieve block body
            let block = match light.retrieve_block(hash).await? {
                None => return Ok(None),
                Some(b) => b,
            };

            let inner = consensus_graph
                .as_any()
                .downcast_ref::<ConsensusGraph>()
                .expect("downcast should succeed")
                .inner
                .read();

            Ok(Some(RpcBlock::new(
                &block,
                *light.get_network_type(),
                &*consensus_graph,
                &*inner,
                &data_man,
                include_txs,
                Some(Space::Native),
            )?))
        };

        Box::new(fut.boxed().compat())
    }

    pub fn blocks_by_epoch(&self, epoch: EpochNumber) -> RpcResult<Vec<H256>> {
        info!("RPC Request: cfx_getBlocksByEpoch epoch_number={:?}", epoch);

        let height = self
            .light
            .get_height_from_epoch_number(epoch.into())
            .map_err(|e| e.to_string())
            .map_err(RpcError::invalid_params)?;

        let hashes = self
            .consensus
            .as_any()
            .downcast_ref::<ConsensusGraph>()
            .expect("downcast should succeed")
            .inner
            .read()
            .block_hashes_by_epoch(height)
            .map_err(|e| e.to_string())
            .map_err(RpcError::invalid_params)?;

        Ok(hashes)
    }

    pub fn gas_price(&self) -> RpcBoxFuture<U256> {
        info!("RPC Request: cfx_gasPrice");

        let light = self.light.clone();

        let fut = async move {
            Ok(light
                .gas_price()
                .await
                .map_err(|e| e.to_string())
                .map_err(RpcError::invalid_params)?
                .unwrap_or(GAS_PRICE_DEFAULT_VALUE.into()))
        };

        Box::new(fut.boxed().compat())
    }

    pub fn interest_rate(
        &self, epoch: Option<EpochNumber>,
    ) -> RpcBoxFuture<U256> {
        let epoch = epoch.unwrap_or(EpochNumber::LatestState).into();
        info!("RPC Request: cfx_getInterestRate epoch={:?}", epoch);

        // clone to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            Ok(light
                .get_interest_rate(epoch)
                .await
                .map_err(|e| e.to_string())
                .map_err(RpcError::invalid_params)?)
        };

        Box::new(fut.boxed().compat())
    }

    pub fn accumulate_interest_rate(
        &self, epoch: Option<EpochNumber>,
    ) -> RpcBoxFuture<U256> {
        let epoch = epoch.unwrap_or(EpochNumber::LatestState).into();

        info!(
            "RPC Request: cfx_getAccumulateInterestRate epoch={:?}",
            epoch
        );

        // clone to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            Ok(light
                .get_accumulate_interest_rate(epoch)
                .await
                .map_err(|e| e.to_string())
                .map_err(RpcError::invalid_params)?)
        };

        Box::new(fut.boxed().compat())
    }

    pub fn pos_economics(
        &self, epoch: Option<EpochNumber>,
    ) -> RpcBoxFuture<PoSEconomics> {
        let epoch = epoch.unwrap_or(EpochNumber::LatestState).into();

        info!("RPC Request: cfx_getPoSEconomics epoch={:?}", epoch);

        // clone to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            Ok(light
                .get_pos_economics(epoch)
                .await
                .map(|ans| PoSEconomics {
                    total_pos_staking_tokens: ans[0],
                    distributable_pos_interest: ans[1],
                    last_distribute_block: ans[2].as_u64().into(),
                })
                .map_err(|e| e.to_string())
                .map_err(RpcError::invalid_params)?)
        };

        Box::new(fut.boxed().compat())
    }

    fn check_balance_against_transaction(
        &self, account_addr: RpcAddress, contract_addr: RpcAddress,
        gas_limit: U256, gas_price: U256, storage_limit: U256,
        epoch: Option<EpochNumber>,
    ) -> RpcBoxFuture<CheckBalanceAgainstTransactionResponse>
    {
        let epoch: primitives::EpochNumber =
            epoch.unwrap_or(EpochNumber::LatestState).into();

        info!(
            "RPC Request: cfx_checkBalanceAgainstTransaction account_addr={:?} contract_addr={:?} gas_limit={:?} gas_price={:?} storage_limit={:?} epoch={:?}",
            account_addr, contract_addr, gas_limit, gas_price, storage_limit, epoch
        );

        // clone to avoid lifetime issues due to capturing `self`
        let light = self.light.clone();

        let fut = async move {
            Self::check_address_network(account_addr.network, &light)?;
            Self::check_address_network(contract_addr.network, &light)?;

            let account_addr: H160 = account_addr.into();
            let contract_addr: H160 = contract_addr.into();

            if storage_limit > U256::from(std::u64::MAX) {
                bail!(RpcError::invalid_params(format!("storage_limit has to be within the range of u64 but {} supplied!", storage_limit)));
            }

            // retrieve accounts and sponsor info in parallel
            let (user_account, contract_account, is_sponsored) =
                future::try_join3(
                    light.get_account(epoch.clone(), account_addr),
                    light.get_account(epoch.clone(), contract_addr),
                    light.is_user_sponsored(epoch, contract_addr, account_addr),
                )
                .await?;

            Ok(common::check_balance_against_transaction(
                user_account,
                contract_account,
                is_sponsored,
                gas_limit,
                gas_price,
                storage_limit,
            ))
        };

        Box::new(fut.boxed().compat())
    }
}

pub struct CfxHandler {
    common: Arc<CommonImpl>,
    rpc_impl: Arc<RpcImpl>,
}

impl CfxHandler {
    pub fn new(common: Arc<CommonImpl>, rpc_impl: Arc<RpcImpl>) -> Self {
        CfxHandler { common, rpc_impl }
    }
}

impl Cfx for CfxHandler {
    delegate! {
        to self.common {
            fn best_block_hash(&self) -> JsonRpcResult<H256>;
            fn confirmation_risk_by_hash(&self, block_hash: H256) -> JsonRpcResult<Option<U256>>;
            fn get_client_version(&self) -> JsonRpcResult<String>;
            fn get_status(&self) -> JsonRpcResult<RpcStatus>;
            fn skipped_blocks_by_epoch(&self, num: EpochNumber) -> JsonRpcResult<Vec<H256>>;
            fn account_pending_info(&self, addr: RpcAddress) -> BoxFuture<Option<AccountPendingInfo>>;
        }

        to self.rpc_impl {
            fn load_test(&self) -> BoxFuture<U256>;
            fn account(&self, address: RpcAddress, num: Option<EpochNumber>) -> BoxFuture<RpcAccount>;
            fn accumulate_interest_rate(&self, num: Option<EpochNumber>) -> BoxFuture<U256>;
            fn admin(&self, address: RpcAddress, num: Option<EpochNumber>) -> BoxFuture<Option<RpcAddress>>;
            fn balance(&self, address: RpcAddress, block_hash_or_epoch_number: Option<BlockHashOrEpochNumber>) -> BoxFuture<U256>;
            fn block_by_epoch_number(&self, epoch_num: EpochNumber, include_txs: bool) -> BoxFuture<Option<RpcBlock>>;
            fn block_by_hash_with_pivot_assumption(&self, block_hash: H256, pivot_hash: H256, epoch_number: U64) -> BoxFuture<RpcBlock>;
            fn block_by_hash(&self, hash: H256, include_txs: bool) -> BoxFuture<Option<RpcBlock>>;
            fn blocks_by_epoch(&self, num: EpochNumber) -> JsonRpcResult<Vec<H256>>;
            fn check_balance_against_transaction(&self, account_addr: RpcAddress, contract_addr: RpcAddress, gas_limit: U256, gas_price: U256, storage_limit: U256, epoch: Option<EpochNumber>) -> BoxFuture<CheckBalanceAgainstTransactionResponse>;
            fn code(&self, address: RpcAddress, block_hash_or_epoch_num: Option<BlockHashOrEpochNumber>) -> BoxFuture<Bytes>;
            fn collateral_for_storage(&self, address: RpcAddress, num: Option<EpochNumber>) -> BoxFuture<U256>;
            fn deposit_list(&self, address: RpcAddress, num: Option<EpochNumber>) -> BoxFuture<Vec<DepositInfo>>;
            fn epoch_number(&self, epoch_num: Option<EpochNumber>) -> JsonRpcResult<U256>;
            fn gas_price(&self) -> BoxFuture<U256>;
            fn get_logs(&self, filter: CfxRpcLogFilter) -> BoxFuture<Vec<RpcLog>>;
            fn interest_rate(&self, num: Option<EpochNumber>) -> BoxFuture<U256>;
            fn next_nonce(&self, address: RpcAddress, num: Option<BlockHashOrEpochNumber>) -> BoxFuture<U256>;
            fn pos_economics(&self, num: Option<EpochNumber>) -> BoxFuture<PoSEconomics>;
            fn send_raw_transaction(&self, raw: Bytes) -> JsonRpcResult<H256>;
            fn sponsor_info(&self, address: RpcAddress, num: Option<EpochNumber>) -> BoxFuture<SponsorInfo>;
            fn staking_balance(&self, address: RpcAddress, num: Option<EpochNumber>) -> BoxFuture<U256>;
            fn storage_at(&self, addr: RpcAddress, pos: U256, block_hash_or_epoch_number: Option<BlockHashOrEpochNumber>) -> BoxFuture<Option<H256>>;
            fn storage_root(&self, address: RpcAddress, epoch_num: Option<EpochNumber>) -> BoxFuture<Option<StorageRoot>>;
            fn transaction_by_hash(&self, hash: H256) -> BoxFuture<Option<RpcTransaction>>;
            fn transaction_receipt(&self, tx_hash: H256) -> BoxFuture<Option<RpcReceipt>>;
            fn vote_list(&self, address: RpcAddress, num: Option<EpochNumber>) -> BoxFuture<Vec<VoteStakeInfo>>;
        }
    }

    // TODO(thegaram): add support for these
    not_supported! {
        fn account_pending_transactions(&self, address: RpcAddress, maybe_start_nonce: Option<U256>, maybe_limit: Option<U64>) -> BoxFuture<AccountPendingTransactions>;
        fn block_by_block_number(&self, block_number: U64, include_txs: bool) -> BoxFuture<Option<RpcBlock>>;
        fn call(&self, request: CallRequest, block_hash_or_epoch_number: Option<BlockHashOrEpochNumber>) -> JsonRpcResult<Bytes>;
        fn estimate_gas_and_collateral(&self, request: CallRequest, epoch_num: Option<EpochNumber>) -> JsonRpcResult<EstimateGasAndCollateralResponse>;
        fn get_block_reward_info(&self, num: EpochNumber) -> JsonRpcResult<Vec<RpcRewardInfo>>;
        fn get_supply_info(&self, epoch_num: Option<EpochNumber>) -> JsonRpcResult<TokenSupplyInfo>;
        fn get_collateral_info(&self, epoch_num: Option<EpochNumber>) -> JsonRpcResult<StorageCollateralInfo>;
        fn get_vote_params(&self, epoch_num: Option<EpochNumber>) -> JsonRpcResult<VoteParamsInfo>;
        fn get_pos_reward_by_epoch(&self, epoch: EpochNumber) -> JsonRpcResult<Option<PoSEpochReward>>;
    }
}

pub struct TestRpcImpl {
    common: Arc<CommonImpl>,
    // rpc_impl: Arc<RpcImpl>,
}

impl TestRpcImpl {
    pub fn new(common: Arc<CommonImpl>, _rpc_impl: Arc<RpcImpl>) -> Self {
        TestRpcImpl {
            common, /* , rpc_impl */
        }
    }
}

impl TestRpc for TestRpcImpl {
    delegate! {
        to self.common {
            fn add_latency(&self, id: NodeId, latency_ms: f64) -> JsonRpcResult<()>;
            fn add_peer(&self, node_id: NodeId, address: SocketAddr) -> JsonRpcResult<()>;
            fn chain(&self) -> JsonRpcResult<Vec<RpcBlock>>;
            fn drop_peer(&self, node_id: NodeId, address: SocketAddr) -> JsonRpcResult<()>;
            fn get_block_count(&self) -> JsonRpcResult<u64>;
            fn get_goodput(&self) -> JsonRpcResult<String>;
            fn get_nodeid(&self, challenge: Vec<u8>) -> JsonRpcResult<Vec<u8>>;
            fn get_peer_info(&self) -> JsonRpcResult<Vec<PeerInfo>>;
            fn save_node_db(&self) -> JsonRpcResult<()>;
            fn say_hello(&self) -> JsonRpcResult<String>;
            fn stop(&self) -> JsonRpcResult<()>;
            fn pos_register(&self, voting_power: U64, version: Option<u8>) -> JsonRpcResult<(Bytes, AccountAddress)>;
            fn pos_update_voting_power(
                &self, pos_account: AccountAddress, increased_voting_power: U64,
            ) -> JsonRpcResult<()>;
            fn pos_stop_election(&self) -> JsonRpcResult<Option<u64>>;
            fn pos_start_voting(&self, initialize: bool) -> JsonRpcResult<()>;
            fn pos_stop_voting(&self) -> JsonRpcResult<()>;
            fn pos_voting_status(&self) -> JsonRpcResult<bool>;
            fn pos_start(&self) -> JsonRpcResult<()>;
            fn pos_force_vote_proposal(&self, block_id: H256) -> JsonRpcResult<()>;
            fn pos_force_propose(&self, round: U64, parent_block_id: H256, payload: Vec<TransactionPayload>) -> JsonRpcResult<()>;
            fn pos_trigger_timeout(&self, timeout_type: String) -> JsonRpcResult<()>;
            fn pos_force_sign_pivot_decision(&self, block_hash: H256, height: U64) -> JsonRpcResult<()>;
            fn pos_get_chosen_proposal(&self) -> JsonRpcResult<Option<PosBlock>>;
        }
    }

    not_supported! {
        fn expire_block_gc(&self, timeout: u64) -> JsonRpcResult<()>;
        fn generate_block_with_blame_info(&self, num_txs: usize, block_size_limit: usize, blame_info: BlameInfo) -> JsonRpcResult<H256>;
        fn generate_block_with_fake_txs(&self, raw_txs_without_data: Bytes, adaptive: Option<bool>, tx_data_len: Option<usize>) -> JsonRpcResult<H256>;
        fn generate_block_with_nonce_and_timestamp(&self, parent: H256, referees: Vec<H256>, raw: Bytes, nonce: U256, timestamp: u64, adaptive: bool) -> JsonRpcResult<H256>;
        fn generate_custom_block(&self, parent_hash: H256, referee: Vec<H256>, raw_txs: Bytes, adaptive: Option<bool>, custom: Option<Vec<Bytes>>) -> JsonRpcResult<H256>;
        fn generate_empty_blocks(&self, num_blocks: usize) -> JsonRpcResult<Vec<H256>>;
        fn generate_fixed_block(&self, parent_hash: H256, referee: Vec<H256>, num_txs: usize, adaptive: bool, difficulty: Option<u64>, pos_reference: Option<H256>) -> JsonRpcResult<H256>;
        fn generate_one_block_with_direct_txgen(&self, num_txs: usize, block_size_limit: usize, num_txs_simple: usize, num_txs_erc20: usize) -> JsonRpcResult<H256>;
        fn generate_one_block(&self, num_txs: usize, block_size_limit: usize) -> JsonRpcResult<H256>;
        fn get_block_status(&self, block_hash: H256) -> JsonRpcResult<(u8, bool)>;
        fn get_executed_info(&self, block_hash: H256) -> JsonRpcResult<(H256, H256)> ;
        fn get_pivot_chain_and_weight(&self, height_range: Option<(u64, u64)>) -> JsonRpcResult<Vec<(H256, U256)>>;
        fn send_usable_genesis_accounts(&self, account_start_index: usize) -> JsonRpcResult<Bytes>;
        fn set_db_crash(&self, crash_probability: f64, crash_exit_code: i32) -> JsonRpcResult<()>;
    }
}

pub struct DebugRpcImpl {
    common: Arc<CommonImpl>,
    rpc_impl: Arc<RpcImpl>,
}

impl DebugRpcImpl {
    pub fn new(common: Arc<CommonImpl>, rpc_impl: Arc<RpcImpl>) -> Self {
        DebugRpcImpl { common, rpc_impl }
    }
}

impl LocalRpc for DebugRpcImpl {
    delegate! {
        to self.common {
            fn txpool_content(&self, address: Option<RpcAddress>) -> JsonRpcResult<
                BTreeMap<String, BTreeMap<String, BTreeMap<usize, Vec<RpcTransaction>>>>>;
            fn txpool_inspect(&self, address: Option<RpcAddress>) -> JsonRpcResult<
                BTreeMap<String, BTreeMap<String, BTreeMap<usize, Vec<String>>>>>;
            fn txpool_get_account_transactions(&self, address: RpcAddress) -> JsonRpcResult<Vec<RpcTransaction>>;
            fn txpool_clear(&self) -> JsonRpcResult<()>;
            fn accounts(&self) -> JsonRpcResult<Vec<RpcAddress>>;
            fn lock_account(&self, address: RpcAddress) -> JsonRpcResult<bool>;
            fn net_disconnect_node(&self, id: NodeId, op: Option<UpdateNodeOperation>) -> JsonRpcResult<bool>;
            fn net_node(&self, id: NodeId) -> JsonRpcResult<Option<(String, Node)>>;
            fn net_sessions(&self, node_id: Option<NodeId>) -> JsonRpcResult<Vec<SessionDetails>>;
            fn net_throttling(&self) -> JsonRpcResult<throttling::Service>;
            fn new_account(&self, password: String) -> JsonRpcResult<RpcAddress>;
            fn sign(&self, data: Bytes, address: RpcAddress, password: Option<String>) -> JsonRpcResult<H520>;
            fn unlock_account(&self, address: RpcAddress, password: String, duration: Option<U128>) -> JsonRpcResult<bool>;
        }

        to self.rpc_impl {
            fn send_transaction(&self, tx: SendTxRequest, password: Option<String>) -> BoxFuture<H256>;
        }
    }

    not_supported! {
        fn consensus_graph_state(&self) -> JsonRpcResult<ConsensusGraphStates>;
        fn current_sync_phase(&self) -> JsonRpcResult<String>;
        fn epoch_receipts(&self, epoch: BlockHashOrEpochNumber, include_eth_recepits: Option<bool>) -> JsonRpcResult<Option<Vec<Vec<RpcReceipt>>>>;
        fn epoch_receipt_proof_by_transaction(&self, tx_hash: H256) -> JsonRpcResult<Option<EpochReceiptProof>>;
        fn sign_transaction(&self, tx: SendTxRequest, password: Option<String>) -> JsonRpcResult<String>;
        fn sync_graph_state(&self) -> JsonRpcResult<SyncGraphStates>;
        fn transactions_by_epoch(&self, epoch_number: U64) -> JsonRpcResult<Vec<WrapTransaction>>;
        fn transactions_by_block(&self, block_hash: H256) -> JsonRpcResult<Vec<WrapTransaction>>;
    }
}
