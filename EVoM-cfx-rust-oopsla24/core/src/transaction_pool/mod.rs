// Copyright 2019 Conflux Foundation. All rights reserved.
// Conflux is free software and distributed under GNU General Public License.
// See http://www.gnu.org/licenses/

#![cfg_attr(feature = "bypass-txpool", allow(unused))]
mod impls;

#[cfg(test)]
mod test_treap;

mod account_cache;
mod garbage_collector;
mod nonce_pool;
mod transaction_pool_inner;

extern crate rand;

pub use self::{impls::TreapMap, transaction_pool_inner::TransactionStatus};
use crate::{
    block_data_manager::BlockDataManager, consensus::BestInformation,
    machine::Machine, state::State, verification::VerificationConfig,
};

use crate::{
    spec::TransitionsEpochHeight,
    transaction_pool::{
        nonce_pool::TxWithReadyInfo, transaction_pool_inner::PendingReason,
    },
    verification::{VerifyTxLocalMode, VerifyTxMode},
    vm::Spec,
};
use account_cache::AccountCache;
use cfx_parameters::block::DEFAULT_TARGET_BLOCK_GAS_LIMIT;
use cfx_statedb::{Result as StateDbResult, StateDb};
use cfx_storage::{StateIndex, StorageManagerTrait};
use cfx_types::{AddressWithSpace as Address, AllChainID, Space, H256, U256};
use malloc_size_of::{MallocSizeOf, MallocSizeOfOps};
use metrics::{
    register_meter_with_group, Gauge, GaugeUsize, Lock, Meter, MeterTimer,
    RwLockExtensions,
};
use parking_lot::{Mutex, RwLock};
use primitives::{
    block::BlockHeight, Account, SignedTransaction, Transaction,
    TransactionWithSignature,
};
#[cfg(feature = "bypass-txpool")]
use std::collections::VecDeque;
use std::{
    cmp::{max, min},
    collections::{hash_map::HashMap, BTreeSet},
    mem,
    ops::DerefMut,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
};
use transaction_pool_inner::TransactionPoolInner;

lazy_static! {
    static ref TX_POOL_DEFERRED_GAUGE: Arc<dyn Gauge<usize>> =
        GaugeUsize::register_with_group("txpool", "stat_deferred_txs");
    static ref TX_POOL_UNPACKED_GAUGE: Arc<dyn Gauge<usize>> =
        GaugeUsize::register_with_group("txpool", "stat_unpacked_txs");
    static ref TX_POOL_READY_GAUGE: Arc<dyn Gauge<usize>> =
        GaugeUsize::register_with_group("txpool", "stat_ready_accounts");
    static ref INSERT_TPS: Arc<dyn Meter> =
        register_meter_with_group("txpool", "insert_tps");
    static ref INSERT_TXS_TPS: Arc<dyn Meter> =
        register_meter_with_group("txpool", "insert_txs_tps");
    static ref INSERT_TXS_SUCCESS_TPS: Arc<dyn Meter> =
        register_meter_with_group("txpool", "insert_txs_success_tps");
    static ref INSERT_TXS_FAILURE_TPS: Arc<dyn Meter> =
        register_meter_with_group("txpool", "insert_txs_failure_tps");
    static ref TX_POOL_INSERT_TIMER: Arc<dyn Meter> =
        register_meter_with_group("timer", "tx_pool::insert_new_tx");
    static ref TX_POOL_VERIFY_TIMER: Arc<dyn Meter> =
        register_meter_with_group("timer", "tx_pool::verify");
    static ref TX_POOL_GET_STATE_TIMER: Arc<dyn Meter> =
        register_meter_with_group("timer", "tx_pool::get_state");
    static ref INSERT_TXS_QUOTA_LOCK: Lock =
        Lock::register("txpool_insert_txs_quota_lock");
    static ref INSERT_TXS_ENQUEUE_LOCK: Lock =
        Lock::register("txpool_insert_txs_enqueue_lock");
    static ref PACK_TRANSACTION_LOCK: Lock =
        Lock::register("txpool_pack_transactions");
    static ref NOTIFY_BEST_INFO_LOCK: Lock =
        Lock::register("txpool_notify_best_info");
    static ref NOTIFY_MODIFIED_LOCK: Lock =
        Lock::register("txpool_notify_modified_info");
    static ref BENCH_INSERT_LOCK: Lock =
        Lock::register("lock");
}


pub struct TxPoolConfig {
    pub capacity: usize,
    pub min_native_tx_price: u64,
    pub min_eth_tx_price: u64,
    pub max_tx_gas: RwLock<U256>,
    pub tx_weight_scaling: u64,
    pub tx_weight_exp: u8,
    pub packing_gas_limit_block_count: u64,
    pub target_block_gas_limit: u64,
}

impl MallocSizeOf for TxPoolConfig {
    fn size_of(&self, _ops: &mut MallocSizeOfOps) -> usize { 0 }
}

impl Default for TxPoolConfig {
    fn default() -> Self {
        TxPoolConfig {
            // Vlad
            capacity: 500_000_000_000,
            min_native_tx_price: 1,
            min_eth_tx_price: 1,
            max_tx_gas: RwLock::new(U256::from(
                DEFAULT_TARGET_BLOCK_GAS_LIMIT / 2,
            )),
            // TODO: Set a proper default scaling since tx pool uses u128 as
            // weight.
            tx_weight_scaling: 1,
            tx_weight_exp: 1,
            packing_gas_limit_block_count: 10,
            target_block_gas_limit: DEFAULT_TARGET_BLOCK_GAS_LIMIT,
        }
    }
}

pub struct TransactionPool {
    pub config: TxPoolConfig,
    verification_config: VerificationConfig,
    inner: RwLock<TransactionPoolInner>,
    to_propagate_trans: Arc<RwLock<HashMap<H256, Arc<SignedTransaction>>>>,
    pub data_man: Arc<BlockDataManager>,
    best_executed_state: Mutex<Arc<State>>,
    consensus_best_info: Mutex<Arc<BestInformation>>,
    set_tx_requests: Mutex<Vec<Arc<SignedTransaction>>>,
    recycle_tx_requests: Mutex<Vec<Arc<SignedTransaction>>>,
    machine: Arc<Machine>,

    /// If it's `false`, operations on the tx pool will be ignored to save
    /// memory/CPU cost.
    ready_for_mining: AtomicBool,
}

impl MallocSizeOf for TransactionPool {
    fn size_of(&self, ops: &mut MallocSizeOfOps) -> usize {
        let inner_size = self.inner.read().size_of(ops);
        let to_propagate_trans_size =
            self.to_propagate_trans.read().size_of(ops);
        let consensus_best_info_size =
            self.consensus_best_info.lock().size_of(ops);
        let set_tx_requests_size = self.set_tx_requests.lock().size_of(ops);
        let recycle_tx_requests_size =
            self.recycle_tx_requests.lock().size_of(ops);
        self.config.size_of(ops)
            + inner_size
            + to_propagate_trans_size
            + self.data_man.size_of(ops)
            + consensus_best_info_size
            + set_tx_requests_size
            + recycle_tx_requests_size
        // Does not count size_of machine
    }
}

pub type SharedTransactionPool = Arc<TransactionPool>;

impl TransactionPool {
    pub fn new(
        config: TxPoolConfig, verification_config: VerificationConfig,
        data_man: Arc<BlockDataManager>, machine: Arc<Machine>,
    ) -> Self
    {
        let genesis_hash = data_man.true_genesis.hash();
        // Vlad
        let inner = TransactionPoolInner::new(
            config.capacity + 500_000_000_000_000,
            config.tx_weight_scaling,
            config.tx_weight_exp,
            (config.packing_gas_limit_block_count
                * config.target_block_gas_limit)
                .into(),
        );
        let best_executed_state = Mutex::new(
            Self::best_executed_state(
                &data_man,
                StateIndex::new_for_readonly(
                    &genesis_hash,
                    &data_man.true_genesis_state_root(),
                ),
            )
            .expect("The genesis state is guaranteed to exist."),
        );
        TransactionPool {
            config,
            verification_config,
            inner: RwLock::new(inner),
            to_propagate_trans: Arc::new(RwLock::new(HashMap::new())),
            data_man: data_man.clone(),
            best_executed_state,
            consensus_best_info: Mutex::new(Arc::new(Default::default())),
            set_tx_requests: Mutex::new(Default::default()),
            recycle_tx_requests: Mutex::new(Default::default()),
            machine,
            ready_for_mining: AtomicBool::new(false),
        }
    }

    pub fn machine(&self) -> Arc<Machine> { self.machine.clone() }

    pub fn get_transaction(
        &self, tx_hash: &H256,
    ) -> Option<Arc<SignedTransaction>> {
        self.inner.read().get(tx_hash)
    }

    pub fn get_transaction_by_address2nonce(
        &self, address: Address, nonce: U256,
    ) -> Option<Arc<SignedTransaction>> {
        self.inner.read().get_by_address2nonce(address, nonce)
    }

    pub fn check_tx_packed_in_deferred_pool(&self, tx_hash: &H256) -> bool {
        self.inner.read().check_tx_packed_in_deferred_pool(tx_hash)
    }

    pub fn get_local_account_info(&self, address: &Address) -> (U256, U256) {
        self.inner
            .read()
            .get_local_nonce_and_balance(address)
            .unwrap_or((0.into(), 0.into()))
    }

    pub fn get_next_nonce(&self, address: &Address) -> U256 {
        let (state_nonce, _) = self
            .get_state_account_info(address)
            .unwrap_or((0.into(), 0.into()));
        self.inner.read().get_next_nonce(address, state_nonce)
    }

    pub fn get_account_pending_info(
        &self, address: &Address,
    ) -> Option<(U256, U256, U256, H256)> {
        self.inner.read().get_account_pending_info(address)
    }

    /// Return `(pending_txs, first_tx_status, pending_count)`.
    pub fn get_account_pending_transactions(
        &self, address: &Address, maybe_start_nonce: Option<U256>,
        maybe_limit: Option<usize>, best_height: BlockHeight,
    ) -> (
        Vec<Arc<SignedTransaction>>,
        Option<TransactionStatus>,
        usize,
    )
    {
        let inner = self.inner.read();
        let (txs, mut first_tx_status, pending_count) = inner
            .get_account_pending_transactions(
                address,
                maybe_start_nonce,
                maybe_limit,
            );
        if txs.is_empty() {
            return (txs, first_tx_status, pending_count);
        }

        let first_tx = txs.first().expect("non empty");
        if address.space == Space::Native {
            if let Transaction::Native(tx) = &first_tx.unsigned {
                if VerificationConfig::check_transaction_epoch_bound(
                    tx,
                    best_height,
                    self.verification_config.transaction_epoch_bound,
                ) == -1
                {
                    // If the epoch height is out of bound, overwrite the
                    // pending reason.
                    first_tx_status = Some(TransactionStatus::Pending(
                        PendingReason::OldEpochHeight,
                    ));
                }
            }
        }

        if matches!(
            first_tx_status,
            Some(TransactionStatus::Ready)
                | Some(TransactionStatus::Pending(
                    PendingReason::NotEnoughCash
                ))
        ) {
            // The sponsor status may have changed, check again.
            // This is not applied to the tx pool state because this check is
            // only triggered on the RPC server.
            let account_cache = self.get_best_state_account_cache();
            match inner.get_sponsored_gas_and_storage(&account_cache, &first_tx)
            {
                Ok((sponsored_gas, sponsored_storage)) => {
                    if let Ok((_, balance)) =
                        account_cache.get_nonce_and_balance(&first_tx.sender())
                    {
                        let tx_info = TxWithReadyInfo {
                            transaction: first_tx.clone(),
                            packed: false,
                            sponsored_gas,
                            sponsored_storage,
                        };
                        if tx_info.calc_tx_cost() <= balance {
                            // The tx should have been ready now.
                            if matches!(
                                first_tx_status,
                                Some(TransactionStatus::Pending(
                                    PendingReason::NotEnoughCash
                                ))
                            ) {
                                first_tx_status =
                                    Some(TransactionStatus::Pending(
                                        PendingReason::OutdatedStatus,
                                    ));
                            }
                        } else {
                            if matches!(
                                first_tx_status,
                                Some(TransactionStatus::Ready)
                            ) {
                                first_tx_status =
                                    Some(TransactionStatus::Pending(
                                        PendingReason::OutdatedStatus,
                                    ));
                            }
                        }
                    }
                }
                Err(e) => {
                    error!(
                        "error in get_account_pending_transactions: e={:?}",
                        e
                    );
                }
            }
        }
        (txs, first_tx_status, pending_count)
    }

    pub fn get_pending_transaction_hashes_in_evm_pool(&self) -> BTreeSet<H256> {
        self.inner.read().ready_transacton_hashes_in_evm_pool()
    }

    pub fn get_pending_transaction_hashes_in_native_pool(
        &self,
    ) -> BTreeSet<H256> {
        self.inner.read().ready_transacton_hashes_in_native_pool()
    }

    pub fn get_state_account_info(
        &self, address: &Address,
    ) -> StateDbResult<(U256, U256)> {
        let account_cache = self.get_best_state_account_cache();
        account_cache.get_nonce_and_balance(address)
    }

    pub fn calc_max_tx_gas(&self) -> U256 {
        let current_best_info = self.consensus_best_info.lock().clone();
        match self
            .data_man
            .block_from_db(&current_best_info.best_block_hash)
        {
            Some(pivot_block) => pivot_block.block_header.gas_limit() / 2,
            None => *self.config.max_tx_gas.read(),
        }
    }


    #[cfg(feature = "bypass-txpool")]
    pub fn insert_new_transactions(
        &self, transactions: Vec<TransactionWithSignature>,
    ) -> (Vec<Arc<SignedTransaction>>, HashMap<H256, String>) {
        INSERT_TPS.mark(1);
        INSERT_TXS_TPS.mark(transactions.len());

        let txs: Vec<Arc<SignedTransaction>> = transactions
            .into_iter()
            .map(|tx| {
                Arc::new(SignedTransaction::new(
                    tx.recover_public().unwrap(),
                    tx,
                ))
            })
            .collect();
        self.inner
            .write_with_metric(&BENCH_INSERT_LOCK)
            .bench_transaction_queue
            .extend(txs.clone());

        (txs, Default::default())
    }


    /// Try to insert `transactions` into transaction pool.
    ///
    /// If some tx is already in our tx_cache, it will be ignored and will not
    /// be added to returned `passed_transactions`. If some tx invalid or
    /// cannot be inserted to the tx pool, it will be included in the returned
    /// `failure` and will not be propagated.
    #[cfg(not(feature = "bypass-txpool"))]
    pub fn insert_new_transactions(
        &self, mut transactions: Vec<TransactionWithSignature>,
    ) -> (Vec<Arc<SignedTransaction>>, HashMap<H256, String>) {
        INSERT_TPS.mark(1);
        INSERT_TXS_TPS.mark(transactions.len());
        let _timer = MeterTimer::time_func(TX_POOL_INSERT_TIMER.as_ref());

        let mut passed_transactions = Vec::new();
        let mut failure = HashMap::new();
        let current_best_info = self.consensus_best_info.lock().clone();

        // filter out invalid transactions.
        let mut index = 0;

        let (chain_id, best_height, best_block_number) = {
            (
                current_best_info.best_chain_id(),
                current_best_info.best_epoch_number,
                current_best_info.best_block_number,
            )
        };
        // FIXME: Needs further discussion here, some transactions may be valid
        // and invalid back and forth does this matters? But for the epoch
        // height check, it may also become valid and invalid back and forth.
        let vm_spec = self.machine.spec(best_block_number);
        let transitions = &self.machine.params().transition_heights;

        while let Some(tx) = transactions.get(index) {
            match self.verify_transaction_tx_pool(
                tx,
                /* basic_check = */ true,
                chain_id,
                best_height,
                transitions,
                &vm_spec,
            ) {
                Ok(_) => index += 1,
                Err(e) => {
                    let removed = transactions.swap_remove(index);
                    debug!("failed to insert tx into pool (validation failed), hash = {:?}, error = {:?}", removed.hash, e);
                    failure.insert(removed.hash, e);
                }
            }
        }

        if transactions.is_empty() {
            INSERT_TXS_SUCCESS_TPS.mark(passed_transactions.len());
            INSERT_TXS_FAILURE_TPS.mark(failure.len());
            return (passed_transactions, failure);
        }

        // Recover public key and insert into pool with readiness check.
        // Note, the workload of recovering public key is very heavy, especially
        // in case of high TPS (e.g. > 8000). So, it's better to recover public
        // key after basic verification.
        match self.data_man.recover_unsigned_tx(&transactions) {
            Ok(signed_trans) => {
                let account_cache = self.get_best_state_account_cache();
                let mut inner =
                    self.inner.write_with_metric(&INSERT_TXS_ENQUEUE_LOCK);
                let mut to_prop = self.to_propagate_trans.write();

                for tx in signed_trans {
                    if inner.get(&tx.hash).is_none() {
                        if let Err(e) = self
                            .add_transaction_with_readiness_check(
                                &mut *inner,
                                &account_cache,
                                tx.clone(),
                                false,
                                false,
                            )
                        {
                            debug!(
                            "tx {:?} fails to be inserted to pool, err={:?}",
                            &tx.hash, e
                        );
                            failure.insert(tx.hash(), e);
                            continue;
                        }
                        passed_transactions.push(tx.clone());
                        if !to_prop.contains_key(&tx.hash)
                            && to_prop.len() < inner.capacity()
                        {
                            to_prop.insert(tx.hash, tx);
                        }
                    }
                }
            }
            Err(e) => {
                for tx in transactions {
                    failure.insert(tx.hash(), format!("{:?}", e).into());
                }
            }
        }

        TX_POOL_DEFERRED_GAUGE.update(self.total_deferred());
        TX_POOL_UNPACKED_GAUGE.update(self.total_unpacked());
        TX_POOL_READY_GAUGE.update(self.total_ready_accounts());

        INSERT_TXS_SUCCESS_TPS.mark(passed_transactions.len());
        INSERT_TXS_FAILURE_TPS.mark(failure.len());

        (passed_transactions, failure)
    }

    /// Try to insert `signed_transaction` into transaction pool.
    ///
    /// If some tx is already in our tx_cache, it will be ignored and will not
    /// be added to returned `passed_transactions`. If some tx invalid or
    /// cannot be inserted to the tx pool, it will be included in the returned
    /// `failure` and will not be propagated.
    pub fn insert_new_signed_transactions(
        &self, mut signed_transactions: Vec<Arc<SignedTransaction>>,
    ) -> (Vec<Arc<SignedTransaction>>, HashMap<H256, String>) {
        INSERT_TPS.mark(1);
        INSERT_TXS_TPS.mark(signed_transactions.len());
        let _timer = MeterTimer::time_func(TX_POOL_INSERT_TIMER.as_ref());

        let mut passed_transactions = Vec::new();
        let mut failure = HashMap::new();
        let current_best_info = { self.consensus_best_info.lock().clone() };

        // filter out invalid transactions.
        let mut index = 0;

        let (chain_id, best_height, best_block_number) = {
            (
                current_best_info.best_chain_id(),
                current_best_info.best_epoch_number,
                current_best_info.best_block_number,
            )
        };
        // FIXME: Needs further discussion here, some transactions may be valid
        // and invalid back and forth does this matters?
        let vm_spec = self.machine.spec(best_block_number);
        let transitions = &self.machine.params().transition_heights;

        while let Some(tx) = signed_transactions.get(index) {
            match self.verify_transaction_tx_pool(
                &tx.transaction,
                true, /* basic_check = */
                chain_id,
                best_height,
                transitions,
                &vm_spec,
            ) {
                Ok(_) => index += 1,
                Err(e) => {
                    let removed = signed_transactions.swap_remove(index);
                    debug!("failed to insert tx into pool (validation failed), hash = {:?}, error = {:?}", removed.hash, e);
                    failure.insert(removed.hash, e);
                }
            }
        }

        // ensure the pool has enough quota to insert new signed transactions.
        let quota = self
            .inner
            .write_with_metric(&INSERT_TXS_QUOTA_LOCK)
            .remaining_quota();
        if quota < signed_transactions.len() {
            for tx in signed_transactions.split_off(quota) {
                trace!("failed to insert tx into pool (quota not enough), hash = {:?}", tx.hash);
                failure.insert(tx.hash, "txpool is full".into());
            }
        }

        if signed_transactions.is_empty() {
            INSERT_TXS_SUCCESS_TPS.mark(passed_transactions.len());
            INSERT_TXS_FAILURE_TPS.mark(failure.len());
            return (passed_transactions, failure);
        }

        // Insert into pool with readiness check.
        // Notice it does not recover the public as the input transactions are
        // already signed.

        {
            let account_cache = self.get_best_state_account_cache();
            let mut inner =
                self.inner.write_with_metric(&INSERT_TXS_ENQUEUE_LOCK);
            let mut to_prop = self.to_propagate_trans.write();

            for tx in signed_transactions {
                if let Err(e) = self.add_transaction_with_readiness_check(
                    &mut *inner,
                    &account_cache,
                    tx.clone(),
                    false,
                    false,
                ) {
                    debug!(
                        "tx {:?} fails to be inserted to pool, err={:?}",
                        &tx.hash, e
                    );
                    failure.insert(tx.hash(), e);
                    continue;
                }
                passed_transactions.push(tx.clone());
                if !to_prop.contains_key(&tx.hash) {
                    to_prop.insert(tx.hash, tx);
                }
            }
            //RwLock is dropped here
        }

        TX_POOL_DEFERRED_GAUGE.update(self.total_deferred());
        TX_POOL_UNPACKED_GAUGE.update(self.total_unpacked());
        TX_POOL_READY_GAUGE.update(self.total_ready_accounts());

        INSERT_TXS_SUCCESS_TPS.mark(passed_transactions.len());
        INSERT_TXS_FAILURE_TPS.mark(failure.len());

        (passed_transactions, failure)
    }

    /// verify transactions based on the rules that have nothing to do with
    /// readiness
    fn verify_transaction_tx_pool(
        &self, transaction: &TransactionWithSignature, basic_check: bool,
        chain_id: AllChainID, best_height: u64,
        transitions: &TransitionsEpochHeight, spec: &Spec,
    ) -> Result<(), String>
    {
        let _timer = MeterTimer::time_func(TX_POOL_VERIFY_TIMER.as_ref());
        let mode = VerifyTxMode::Local(VerifyTxLocalMode::MaybeLater, spec);

        if basic_check {
            self.verification_config
                .check_tx_size(transaction)
                .map_err(|e| e.to_string())?;
            if let Err(e) = self.verification_config.verify_transaction_common(
                transaction,
                chain_id,
                best_height,
                transitions,
                mode,
            ) {
                warn!("Transaction {:?} discarded due to not passing basic verification.", transaction.hash());
                return Err(format!("{:?}", e));
            }
        }

        // Check the epoch height is moved to verify_transaction_common. In
        // VerifyTxLocalMode::MaybeLater mode, a transaction with larger target
        // epoch can be accepted. Since PR #1610, it is guaranteed that
        // best info is initialized here.

        // check transaction gas limit
        let max_tx_gas = *self.config.max_tx_gas.read();
        if *transaction.gas() > max_tx_gas {
            warn!(
                "Transaction discarded due to above gas limit: {} > {:?}",
                transaction.gas(),
                max_tx_gas
            );
            return Err(format!(
                "transaction gas {} exceeds the maximum value {:?}, the half of pivot block gas limit",
                transaction.gas(), max_tx_gas
            ));
        }

        let min_tx_price = match transaction.space() {
            Space::Native => self.config.min_native_tx_price,
            Space::Ethereum => self.config.min_eth_tx_price,
        };
        // check transaction gas price
        if *transaction.gas_price() < min_tx_price.into() {
            trace!("Transaction {} discarded due to below minimal gas price: price {}", transaction.hash(), transaction.gas_price());
            return Err(format!(
                "transaction gas price {} less than the minimum value {}",
                transaction.gas_price(),
                min_tx_price
            ));
        }

        Ok(())
    }

    // Add transaction into deferred pool and maintain its readiness
    // the packed tag provided
    // if force tag is true, the replacement in nonce pool must be happened
    pub fn add_transaction_with_readiness_check(
        &self, inner: &mut TransactionPoolInner, account_cache: &AccountCache,
        transaction: Arc<SignedTransaction>, packed: bool, force: bool,
    ) -> Result<(), String>
    {
        inner.insert_transaction_with_readiness_check(
            account_cache,
            transaction,
            packed,
            force,
        )
    }

    pub fn get_to_be_propagated_transactions(
        &self,
    ) -> HashMap<H256, Arc<SignedTransaction>> {
        let mut to_prop = self.to_propagate_trans.write();
        let mut res = HashMap::new();
        mem::swap(&mut *to_prop, &mut res);
        res
    }

    pub fn set_to_be_propagated_transactions(
        &self, transactions: HashMap<H256, Arc<SignedTransaction>>,
    ) {
        let mut to_prop = self.to_propagate_trans.write();
        to_prop.extend(transactions);
    }

    pub fn remove_to_be_propagated_transactions(&self, tx_hash: &H256) {
        self.to_propagate_trans.write().remove(tx_hash);
    }

    // If a tx is failed executed due to invalid nonce or if its enclosing block
    // becomes orphan due to era transition. This function should be invoked
    // to recycle it
    pub fn recycle_transactions(
        &self, transactions: Vec<Arc<SignedTransaction>>,
    ) {
        if transactions.is_empty() || !self.ready_for_mining() {
            // Fast return.
            return;
        }

        let mut recycle_req_buffer = self.recycle_tx_requests.lock();
        for tx in transactions {
            recycle_req_buffer.push(tx);
        }
    }

    pub fn set_tx_packed(&self, transactions: &Vec<Arc<SignedTransaction>>) {
        if transactions.is_empty() || !self.ready_for_mining() {
            // Fast return.
            return;
        }
        let mut tx_req_buffer = self.set_tx_requests.lock();
        for tx in transactions {
            tx_req_buffer.push(tx.clone());
        }
    }

    pub fn pack_transactions<'a>(
        &self, num_txs: usize, block_gas_limit: U256, evm_gas_limit: U256,
        block_size_limit: usize, mut best_epoch_height: u64,
        mut best_block_number: u64,
    ) -> Vec<Arc<SignedTransaction>>
    {
        let mut inner = self.inner.write_with_metric(&PACK_TRANSACTION_LOCK);
        best_epoch_height += 1;
        // The best block number is not necessary an exact number.
        best_block_number += 1;
        #[cfg(not(feature = "bypass-txpool"))]
        {
            inner.pack_transactions(
                num_txs,
                block_gas_limit,
                evm_gas_limit,
                block_size_limit,
                best_epoch_height,
                best_block_number,
                &self.verification_config,
                &self.machine,
            )
        }
        #[cfg(feature = "bypass-txpool")]
        {
            let mut txs = Vec::with_capacity(10000);
            let mut total_gas = U256::zero();
            let mut total_size = 0;
            let queue: &mut VecDeque<Arc<SignedTransaction>> =
                &mut inner.bench_transaction_queue;
            while let Some(tx) = queue.pop_front() {
                total_size += tx.transaction.rlp_size.unwrap_or(0);
                total_gas += *(tx.transaction.transaction.unsigned.gas());
                if txs.len() >= num_txs
                    || total_size > block_size_limit
                    || total_gas > block_gas_limit
                {
                    // info!(
                    //     "[lvmt] txs {}, size {}/{}, gas {}/{}",
                    //     txs.len(),
                    //     total_size,
                    //     block_size_limit,
                    //     total_gas,
                    //     block_gas_limit
                    // );
                    queue.push_front(tx);
                    break;
                } else {
                    txs.push(tx.clone())
                }
            }
            transaction_pool_inner::TX_POOL_PACK_TRANSACTION_TPS
                .mark(txs.len());

            txs
        }
    }

    pub fn notify_modified_accounts(
        &self, accounts_from_execution: Vec<Account>,
    ) {
        if cfg!(feature = "bypass-txpool") {
            return;
        }
        let mut inner = self.inner.write_with_metric(&NOTIFY_MODIFIED_LOCK);
        inner.notify_modified_accounts(accounts_from_execution)
    }

    pub fn clear_tx_pool(&self) {
        let mut inner = self.inner.write();
        inner.clear()
    }

    pub fn total_deferred(&self) -> usize {
        let inner = self.inner.read();
        inner.total_deferred()
    }

    pub fn total_ready_accounts(&self) -> usize {
        let inner = self.inner.read();
        inner.total_ready_accounts()
    }

    pub fn total_received(&self) -> usize {
        let inner = self.inner.read();
        inner.total_received()
    }

    pub fn total_unpacked(&self) -> usize {
        let inner = self.inner.read();
        inner.total_unpacked()
    }

    /// stats retrieves the length of ready and deferred pool.
    pub fn stats(&self) -> (usize, usize, usize, usize) {
        let inner = self.inner.read();
        (
            inner.total_ready_accounts(),
            inner.total_deferred(),
            inner.total_received(),
            inner.total_unpacked(),
        )
    }

    /// content retrieves the ready and deferred transactions.
    pub fn content(
        &self, address: Option<Address>,
    ) -> (Vec<Arc<SignedTransaction>>, Vec<Arc<SignedTransaction>>) {
        let inner = self.inner.read();
        inner.content(address)
    }

    pub fn notify_new_best_info(
        &self, best_info: Arc<BestInformation>,
    ) -> StateDbResult<()> {
        let mut set_tx_buffer = self.set_tx_requests.lock();
        let mut recycle_tx_buffer = self.recycle_tx_requests.lock();
        {
            let mut consensus_best_info = self.consensus_best_info.lock();
            *consensus_best_info = best_info.clone();
        }
        *self.config.max_tx_gas.write() = self.calc_max_tx_gas();

        if cfg!(feature = "bypass-txpool") {
            return Ok(());
        }

        let account_cache = self.get_best_state_account_cache();
        let mut inner = self.inner.write_with_metric(&NOTIFY_BEST_INFO_LOCK);
        let inner = inner.deref_mut();

        while let Some(tx) = set_tx_buffer.pop() {
            let tx_hash = tx.hash();
            if let Err(e) = self.add_transaction_with_readiness_check(
                inner,
                &account_cache,
                tx,
                true,
                false,
            ) {
                // TODO: A transaction that is packed multiple times would also
                // throw an error here, but it should be normal.
                debug!("set tx err: tx={}, e={:?}", tx_hash, e);
            }
        }

        let (chain_id, best_height, best_block_number) = {
            (
                best_info.best_chain_id(),
                best_info.best_epoch_number,
                best_info.best_block_number,
            )
        };
        // FIXME: Needs further discussion here, some transactions may be valid
        // and invalid back and forth, does this matters?
        let vm_spec = self.machine.spec(best_block_number);
        let transitions = &self.machine.params().transition_heights;

        while let Some(tx) = recycle_tx_buffer.pop() {
            info!(
                "should not trigger recycle transaction, nonce = {}, sender = {:?}, \
                account nonce = {}, hash = {:?} .",
                &tx.nonce(), &tx.sender(),
                account_cache.get_nonce(&tx.sender())?, tx.hash);

            if let Err(e) = self.verify_transaction_tx_pool(
                &tx,
                /* basic_check = */ false,
                chain_id,
                best_height,
                transitions,
                &vm_spec,
            ) {
                warn!(
                    "Recycled transaction {:?} discarded due to not passing verification {}.",
                    tx.hash(), e
                );
            }
            if let Err(e) = self.add_transaction_with_readiness_check(
                inner,
                &account_cache,
                tx,
                false,
                true,
            ) {
                warn!("recycle tx err: e={:?}", e);
            }
        }
        debug!(
            "notify_new_best_info: {:?}",
            self.consensus_best_info.lock()
        );

        Ok(())
    }

    pub fn get_best_info_with_packed_transactions(
        &self, num_txs: usize, block_size_limit: usize,
        additional_transactions: Vec<Arc<SignedTransaction>>,
    ) -> (Arc<BestInformation>, U256, Vec<Arc<SignedTransaction>>)
    {
        // We do not need to hold the lock because it is fine for us to generate
        // blocks that are slightly behind the best state.
        // We do not want to stall the consensus thread.
        let consensus_best_info_clone = self.consensus_best_info.lock().clone();
        debug!(
            "get_best_info_with_packed_transactions: {:?}",
            consensus_best_info_clone
        );

        let parent_block_gas_limit = self
            .data_man
            .block_header_by_hash(&consensus_best_info_clone.best_block_hash)
            // The parent block must exists.
            .expect(&concat!(file!(), ":", line!(), ":", column!()))
            .gas_limit()
            .clone();

        let gas_limit_divisor = self.machine.params().gas_limit_bound_divisor;
        let min_gas_limit = self.machine.params().min_gas_limit;
        assert!(parent_block_gas_limit >= min_gas_limit);
        let gas_lower = max(
            parent_block_gas_limit - parent_block_gas_limit / gas_limit_divisor
                + 1,
            min_gas_limit,
        );
        let gas_upper = parent_block_gas_limit
            + parent_block_gas_limit / gas_limit_divisor
            - 1;

        let target_gas_limit = self.config.target_block_gas_limit.into();
        let self_gas_limit = min(max(target_gas_limit, gas_lower), gas_upper);
        let evm_gas_limit = if self.machine.params().can_pack_evm_transaction(
            consensus_best_info_clone.best_epoch_number + 1,
        ) {
            self_gas_limit / self.machine.params().evm_transaction_gas_ratio
        } else {
            U256::zero()
        };

        let transactions_from_pool = self.pack_transactions(
            num_txs,
            self_gas_limit.clone(),
            evm_gas_limit,
            block_size_limit,
            consensus_best_info_clone.best_epoch_number,
            consensus_best_info_clone.best_block_number,
        );

        let transactions = [
            additional_transactions.as_slice(),
            transactions_from_pool.as_slice(),
        ]
        .concat();

        (consensus_best_info_clone, self_gas_limit, transactions)
    }

    fn best_executed_state(
        data_man: &BlockDataManager, best_executed_epoch: StateIndex,
    ) -> StateDbResult<Arc<State>> {
        Ok(Arc::new(State::new(StateDb::new(
            data_man
                .storage_manager
                .get_state_no_commit(
                    best_executed_epoch,
                    /* try_open = */ false,
                    None,
                )?
                // Safe because the state is guaranteed to be available
                .unwrap(),
        ))?))
    }

    pub fn set_best_executed_epoch(
        &self, best_executed_epoch: StateIndex,
    ) -> StateDbResult<()> {
        *self.best_executed_state.lock() =
            Self::best_executed_state(&self.data_man, best_executed_epoch)?;

        Ok(())
    }

    fn get_best_state_account_cache(&self) -> AccountCache {
        let _timer = MeterTimer::time_func(TX_POOL_GET_STATE_TIMER.as_ref());
        AccountCache::new((&*self.best_executed_state.lock()).clone())
    }

    pub fn ready_for_mining(&self) -> bool {
        self.ready_for_mining.load(Ordering::SeqCst)
    }

    pub fn set_ready(&self) {
        self.ready_for_mining.store(true, Ordering::SeqCst);
    }
}
