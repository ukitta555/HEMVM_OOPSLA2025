// Copyright (c) Aptos
// SPDX-License-Identifier: Apache-2.0

pub mod analyze;

use crate::{
    common::{
        types::{
            CliCommand, CliError, CliResult, CliTypedResult, ConfigSearchMode,
            OptionalPoolAddressArgs, PoolAddressArgs, ProfileOptions, PromptOptions, RestOptions,
            TransactionOptions, TransactionSummary,
        },
        utils::{prompt_yes_with_override, read_from_file},
    },
    config::GlobalConfig,
    genesis::git::from_yaml,
    node::analyze::{
        analyze_validators::{AnalyzeValidators, ValidatorStats},
        fetch_metadata::FetchMetadata,
    },
};
use aptos_backup_cli::{
    coordinators::restore::{RestoreCoordinator, RestoreCoordinatorOpt},
    metadata::cache::MetadataCacheOpt,
    storage::command_adapter::{config::CommandAdapterConfig, CommandAdapter},
    utils::{ConcurrentDownloadsOpt, GlobalRestoreOpt, ReplayConcurrencyLevelOpt, RocksdbOpt},
};
use aptos_cached_packages::aptos_stdlib;
use aptos_config::config::NodeConfig;
use aptos_crypto::{bls12381, bls12381::PublicKey, x25519, ValidCryptoMaterialStringExt};
use aptos_faucet::FaucetArgs;
use aptos_genesis::config::{HostAndPort, OperatorConfiguration};
use aptos_rest_client::{aptos_api_types::VersionedEvent, Client, State};
use aptos_types::{
    account_address::AccountAddress,
    account_config::{BlockResource, CORE_CODE_ADDRESS},
    chain_id::ChainId,
    network_address::NetworkAddress,
    on_chain_config::{ConfigurationResource, ConsensusScheme, ValidatorSet},
    stake_pool::StakePool,
    staking_contract::StakingContractStore,
    transaction::EthAddress,
    validator_info::ValidatorInfo,
    validator_performances::ValidatorPerformances,
    vesting::VestingAdminStore,
};
use async_trait::async_trait;
use bcs::Result;
use chrono::{DateTime, NaiveDateTime, Utc};
use clap::Parser;
use hex::FromHex;
use rand::{rngs::StdRng, SeedableRng};
use reqwest::Url;
use serde::{Deserialize, Serialize};
use std::{
    collections::HashMap,
    convert::{TryFrom, TryInto},
    path::PathBuf,
    pin::Pin,
    sync::Arc,
    thread,
    time::Duration,
};
use tokio::time::Instant;

const SECS_TO_MICROSECS: u64 = 1_000_000;

/// Tool for operations related to nodes
///
/// This tool allows you to run a local test node for testing,
/// identify issues with nodes, and show related information.
#[derive(Parser)]
pub enum NodeTool {
    GetPerformance(GetPerformance),
    GetStakePool(GetStakePool),
    InitializeValidator(InitializeValidator),
    JoinValidatorSet(JoinValidatorSet),
    LeaveValidatorSet(LeaveValidatorSet),
    ShowEpochInfo(ShowEpochInfo),
    ShowValidatorConfig(ShowValidatorConfig),
    ShowValidatorSet(ShowValidatorSet),
    ShowValidatorStake(ShowValidatorStake),
    RunLocalTestnet(RunLocalTestnet),
    UpdateConsensusKey(UpdateConsensusKey),
    UpdateValidatorNetworkAddresses(UpdateValidatorNetworkAddresses),
    AnalyzeValidatorPerformance(AnalyzeValidatorPerformance),
    BootstrapDbFromBackup(BootstrapDbFromBackup),
}

impl NodeTool {
    pub async fn execute(self) -> CliResult {
        use NodeTool::*;
        match self {
            GetPerformance(tool) => tool.execute_serialized().await,
            GetStakePool(tool) => tool.execute_serialized().await,
            InitializeValidator(tool) => tool.execute_serialized().await,
            JoinValidatorSet(tool) => tool.execute_serialized().await,
            LeaveValidatorSet(tool) => tool.execute_serialized().await,
            ShowEpochInfo(tool) => tool.execute_serialized().await,
            ShowValidatorSet(tool) => tool.execute_serialized().await,
            ShowValidatorStake(tool) => tool.execute_serialized().await,
            ShowValidatorConfig(tool) => tool.execute_serialized().await,
            RunLocalTestnet(tool) => tool.execute_serialized_without_logger().await,
            UpdateConsensusKey(tool) => tool.execute_serialized().await,
            UpdateValidatorNetworkAddresses(tool) => tool.execute_serialized().await,
            AnalyzeValidatorPerformance(tool) => tool.execute_serialized().await,
            BootstrapDbFromBackup(tool) => tool.execute_serialized().await,
        }
    }
}

#[derive(Parser)]
pub struct OperatorConfigFileArgs {
    /// Operator Configuration file, created from the `genesis set-validator-configuration` command
    #[clap(long, parse(from_os_str))]
    pub(crate) operator_config_file: Option<PathBuf>,
}

impl OperatorConfigFileArgs {
    fn load(&self) -> CliTypedResult<Option<OperatorConfiguration>> {
        if let Some(ref file) = self.operator_config_file {
            Ok(from_yaml(
                &String::from_utf8(read_from_file(file)?).map_err(CliError::from)?,
            )?)
        } else {
            Ok(None)
        }
    }
}

#[derive(Parser)]
pub struct ValidatorConsensusKeyArgs {
    /// Hex encoded Consensus public key
    ///
    /// The key should be a BLS12-381 public key
    #[clap(long, parse(try_from_str = bls12381::PublicKey::from_encoded_string))]
    pub(crate) consensus_public_key: Option<bls12381::PublicKey>,

    /// Hex encoded Consensus proof of possession
    ///
    /// The key should be a BLS12-381 proof of possession
    #[clap(long, parse(try_from_str = bls12381::ProofOfPossession::from_encoded_string))]
    pub(crate) proof_of_possession: Option<bls12381::ProofOfPossession>,
}

impl ValidatorConsensusKeyArgs {
    fn get_consensus_public_key<'a>(
        &'a self,
        operator_config: &'a Option<OperatorConfiguration>,
    ) -> CliTypedResult<&'a bls12381::PublicKey> {
        let consensus_public_key = if let Some(ref consensus_public_key) = self.consensus_public_key
        {
            consensus_public_key
        } else if let Some(ref operator_config) = operator_config {
            &operator_config.consensus_public_key
        } else {
            return Err(CliError::CommandArgumentError(
                "Must provide either --operator-config-file or --consensus-public-key".to_string(),
            ));
        };
        Ok(consensus_public_key)
    }

    fn get_consensus_proof_of_possession<'a>(
        &'a self,
        operator_config: &'a Option<OperatorConfiguration>,
    ) -> CliTypedResult<&'a bls12381::ProofOfPossession> {
        let proof_of_possession = if let Some(ref proof_of_possession) = self.proof_of_possession {
            proof_of_possession
        } else if let Some(ref operator_config) = operator_config {
            &operator_config.consensus_proof_of_possession
        } else {
            return Err(CliError::CommandArgumentError(
                "Must provide either --operator-config-file or --proof-of-possession".to_string(),
            ));
        };
        Ok(proof_of_possession)
    }
}

#[derive(Parser)]
pub struct ValidatorNetworkAddressesArgs {
    /// Host and port pair for the validator e.g. 127.0.0.1:6180
    #[clap(long)]
    pub(crate) validator_host: Option<HostAndPort>,

    /// Validator x25519 public network key
    #[clap(long, parse(try_from_str = x25519::PublicKey::from_encoded_string))]
    pub(crate) validator_network_public_key: Option<x25519::PublicKey>,

    /// Host and port pair for the fullnode e.g. 127.0.0.1:6180.  Optional
    #[clap(long)]
    pub(crate) full_node_host: Option<HostAndPort>,

    /// Full node x25519 public network key
    #[clap(long, parse(try_from_str = x25519::PublicKey::from_encoded_string))]
    pub(crate) full_node_network_public_key: Option<x25519::PublicKey>,
}

impl ValidatorNetworkAddressesArgs {
    fn get_network_configs<'a>(
        &'a self,
        operator_config: &'a Option<OperatorConfiguration>,
    ) -> CliTypedResult<(
        x25519::PublicKey,
        Option<x25519::PublicKey>,
        &'a HostAndPort,
        Option<&'a HostAndPort>,
    )> {
        let validator_network_public_key =
            if let Some(public_key) = self.validator_network_public_key {
                public_key
            } else if let Some(ref operator_config) = operator_config {
                operator_config.validator_network_public_key
            } else {
                return Err(CliError::CommandArgumentError(
                    "Must provide either --operator-config-file or --validator-network-public-key"
                        .to_string(),
                ));
            };

        let full_node_network_public_key =
            if let Some(public_key) = self.full_node_network_public_key {
                Some(public_key)
            } else if let Some(ref operator_config) = operator_config {
                operator_config.full_node_network_public_key
            } else {
                None
            };

        let validator_host = if let Some(ref host) = self.validator_host {
            host
        } else if let Some(ref operator_config) = operator_config {
            &operator_config.validator_host
        } else {
            return Err(CliError::CommandArgumentError(
                "Must provide either --operator-config-file or --validator-host".to_string(),
            ));
        };

        let full_node_host = if let Some(ref host) = self.full_node_host {
            Some(host)
        } else if let Some(ref operator_config) = operator_config {
            operator_config.full_node_host.as_ref()
        } else {
            None
        };

        Ok((
            validator_network_public_key,
            full_node_network_public_key,
            validator_host,
            full_node_host,
        ))
    }
}

#[derive(Copy, Clone, Debug, Serialize)]
pub enum StakePoolType {
    Direct,
    StakingContract,
    Vesting,
}

#[derive(Copy, Clone, Debug, Eq, PartialEq, Serialize)]
pub enum StakePoolState {
    Active,
    Inactive,
    PendingActive,
    PendingInactive,
}

#[derive(Debug, Serialize)]
pub struct StakePoolResult {
    pub state: StakePoolState,
    pub pool_address: AccountAddress,
    pub operator_address: AccountAddress,
    pub voter_address: AccountAddress,
    pub pool_type: StakePoolType,
    pub total_stake: u64,
    pub commission_percentage: u64,
    pub commission_not_yet_unlocked: u64,
    pub lockup_expiration_utc_time: DateTime<Utc>,
    pub consensus_public_key: String,
    pub validator_network_addresses: Vec<NetworkAddress>,
    pub fullnode_network_addresses: Vec<NetworkAddress>,
    pub epoch_info: EpochInfo,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub vesting_contract: Option<AccountAddress>,
}

/// Show the stake pool
///
/// Retrieves the associated stake pool from the multiple types for the given owner address
#[derive(Parser)]
pub struct GetStakePool {
    /// The owner address of the stake pool
    #[clap(long, parse(try_from_str=crate::common::types::load_account_arg))]
    pub(crate) owner_address: AccountAddress,
    #[clap(flatten)]
    pub(crate) rest_options: RestOptions,
    #[clap(flatten)]
    pub(crate) profile_options: ProfileOptions,
}

#[async_trait]
impl CliCommand<Vec<StakePoolResult>> for GetStakePool {
    fn command_name(&self) -> &'static str {
        "GetStakePool"
    }

    async fn execute(mut self) -> CliTypedResult<Vec<StakePoolResult>> {
        let owner_address = self.owner_address;
        let client = &self.rest_options.client(&self.profile_options)?;
        get_stake_pools(client, owner_address).await
    }
}

#[derive(Debug, Serialize)]
pub struct StakePoolPerformance {
    current_epoch_successful_proposals: u64,
    current_epoch_failed_proposals: u64,
    previous_epoch_rewards: Vec<String>,
    epoch_info: EpochInfo,
}

/// Show staking performance of the given staking pool
#[derive(Parser)]
pub struct GetPerformance {
    #[clap(flatten)]
    pub(crate) pool_address_args: PoolAddressArgs,
    #[clap(flatten)]
    pub(crate) rest_options: RestOptions,
    #[clap(flatten)]
    pub(crate) profile_options: ProfileOptions,
}

#[async_trait]
impl CliCommand<StakePoolPerformance> for GetPerformance {
    fn command_name(&self) -> &'static str {
        "GetPerformance"
    }

    async fn execute(mut self) -> CliTypedResult<StakePoolPerformance> {
        let client = &self.rest_options.client(&self.profile_options)?;
        let pool_address = self.pool_address_args.pool_address;
        let validator_set = &client
            .get_account_resource_bcs::<ValidatorSet>(CORE_CODE_ADDRESS, "0x1::stake::ValidatorSet")
            .await?
            .into_inner();

        let mut current_epoch_successful_proposals = 0;
        let mut current_epoch_failed_proposals = 0;
        let state = get_stake_pool_state(validator_set, &pool_address);
        if state == StakePoolState::Active || state == StakePoolState::PendingInactive {
            let validator_config = client
                .get_account_resource_bcs::<ValidatorConfig>(
                    pool_address,
                    "0x1::stake::ValidatorConfig",
                )
                .await?
                .into_inner();
            let validator_performances = &client
                .get_account_resource_bcs::<ValidatorPerformances>(
                    CORE_CODE_ADDRESS,
                    "0x1::stake::ValidatorPerformance",
                )
                .await?
                .into_inner();
            let validator_index = validator_config.validator_index as usize;
            current_epoch_successful_proposals =
                validator_performances.validators[validator_index].successful_proposals;
            current_epoch_failed_proposals =
                validator_performances.validators[validator_index].failed_proposals;
        };

        let previous_epoch_rewards = client
            .get_account_events(
                pool_address,
                "0x1::stake::StakePool",
                "distribute_rewards_events",
                Some(0),
                Some(10),
            )
            .await
            .unwrap()
            .into_inner()
            .into_iter()
            .map(|e: VersionedEvent| {
                e.data
                    .get("rewards_amount")
                    .unwrap()
                    .as_str()
                    .unwrap()
                    .into()
            })
            .collect();

        Ok(StakePoolPerformance {
            current_epoch_successful_proposals,
            current_epoch_failed_proposals,
            previous_epoch_rewards,
            epoch_info: get_epoch_info(client).await?,
        })
    }
}

/// Retrieves the stake pools associated with an account
pub async fn get_stake_pools(
    client: &Client,
    owner_address: AccountAddress,
) -> CliTypedResult<Vec<StakePoolResult>> {
    let epoch_info = get_epoch_info(client).await?;
    let validator_set = &client
        .get_account_resource_bcs::<ValidatorSet>(CORE_CODE_ADDRESS, "0x1::stake::ValidatorSet")
        .await?
        .into_inner();
    let mut stake_pool_results: Vec<StakePoolResult> = vec![];
    // Add direct stake pool if any.
    let direct_stake_pool = get_stake_pool_info(
        client,
        owner_address,
        StakePoolType::Direct,
        0,
        0,
        epoch_info.clone(),
        validator_set,
        None,
    )
    .await;
    if let Ok(direct_stake_pool) = direct_stake_pool {
        stake_pool_results.push(direct_stake_pool);
    };

    // Fetch all stake pools managed via staking contracts.
    let staking_contract_pools = get_staking_contract_pools(
        client,
        owner_address,
        StakePoolType::StakingContract,
        epoch_info.clone(),
        validator_set,
        None,
    )
    .await;
    if let Ok(mut staking_contract_pools) = staking_contract_pools {
        stake_pool_results.append(&mut staking_contract_pools);
    };

    // Fetch all stake pools managed via employee vesting accounts.
    let vesting_admin_store = client
        .get_account_resource_bcs::<VestingAdminStore>(owner_address, "0x1::vesting::AdminStore")
        .await;
    if let Ok(vesting_admin_store) = vesting_admin_store {
        let vesting_contracts = vesting_admin_store.into_inner().vesting_contracts;
        for vesting_contract in vesting_contracts {
            let mut staking_contract_pools = get_staking_contract_pools(
                client,
                vesting_contract,
                StakePoolType::Vesting,
                epoch_info.clone(),
                validator_set,
                Some(vesting_contract),
            )
            .await
            .unwrap();
            stake_pool_results.append(&mut staking_contract_pools);
        }
    };

    Ok(stake_pool_results)
}

/// Retrieve 0x1::staking_contract related pools
pub async fn get_staking_contract_pools(
    client: &Client,
    staker_address: AccountAddress,
    pool_type: StakePoolType,
    epoch_info: EpochInfo,
    validator_set: &ValidatorSet,
    vesting_contract: Option<AccountAddress>,
) -> CliTypedResult<Vec<StakePoolResult>> {
    let mut stake_pool_results: Vec<StakePoolResult> = vec![];
    let staking_contract_store = client
        .get_account_resource_bcs::<StakingContractStore>(
            staker_address,
            "0x1::staking_contract::Store",
        )
        .await?;
    let staking_contracts = staking_contract_store.into_inner().staking_contracts;
    for staking_contract in staking_contracts {
        let stake_pool_address = get_stake_pool_info(
            client,
            staking_contract.value.pool_address,
            pool_type,
            staking_contract.value.principal,
            staking_contract.value.commission_percentage,
            epoch_info.clone(),
            validator_set,
            vesting_contract,
        )
        .await
        .unwrap();
        stake_pool_results.push(stake_pool_address);
    }
    Ok(stake_pool_results)
}

pub async fn get_stake_pool_info(
    client: &Client,
    pool_address: AccountAddress,
    pool_type: StakePoolType,
    principal: u64,
    commission_percentage: u64,
    epoch_info: EpochInfo,
    validator_set: &ValidatorSet,
    vesting_contract: Option<AccountAddress>,
) -> CliTypedResult<StakePoolResult> {
    let stake_pool = client
        .get_account_resource_bcs::<StakePool>(pool_address, "0x1::stake::StakePool")
        .await?
        .into_inner();
    let validator_config = client
        .get_account_resource_bcs::<ValidatorConfig>(pool_address, "0x1::stake::ValidatorConfig")
        .await?
        .into_inner();
    let total_stake = stake_pool.get_total_staked_amount();
    let commission_not_yet_unlocked = (total_stake - principal) * commission_percentage / 100;
    let state = get_stake_pool_state(validator_set, &pool_address);

    let consensus_public_key = if validator_config.consensus_public_key.is_empty() {
        "".into()
    } else {
        PublicKey::try_from(&validator_config.consensus_public_key[..])
            .unwrap()
            .to_encoded_string()
            .unwrap()
    };
    Ok(StakePoolResult {
        state,
        pool_address,
        operator_address: stake_pool.operator_address,
        voter_address: stake_pool.delegated_voter,
        pool_type,
        total_stake,
        commission_percentage,
        commission_not_yet_unlocked,
        lockup_expiration_utc_time: Time::new_seconds(stake_pool.locked_until_secs).utc_time,
        consensus_public_key,
        validator_network_addresses: validator_config
            .validator_network_addresses()
            .unwrap_or_default(),
        fullnode_network_addresses: validator_config
            .fullnode_network_addresses()
            .unwrap_or_default(),
        epoch_info,
        vesting_contract,
    })
}

fn get_stake_pool_state(
    validator_set: &ValidatorSet,
    pool_address: &AccountAddress,
) -> StakePoolState {
    if validator_set.active_validators().contains(pool_address) {
        StakePoolState::Active
    } else if validator_set
        .pending_active_validators()
        .contains(pool_address)
    {
        StakePoolState::PendingActive
    } else if validator_set
        .pending_inactive_validators()
        .contains(pool_address)
    {
        StakePoolState::PendingInactive
    } else {
        StakePoolState::Inactive
    }
}

/// Register the current account as a validator node operator
///
/// This will create a new stake pool for the given account.  The voter and operator fields will be
/// defaulted to the stake pool account if not provided.
#[derive(Parser)]
pub struct InitializeValidator {
    #[clap(flatten)]
    pub(crate) txn_options: TransactionOptions,
    #[clap(flatten)]
    pub(crate) operator_config_file_args: OperatorConfigFileArgs,
    #[clap(flatten)]
    pub(crate) validator_consensus_key_args: ValidatorConsensusKeyArgs,
    #[clap(flatten)]
    pub(crate) validator_network_addresses_args: ValidatorNetworkAddressesArgs,
}

#[async_trait]
impl CliCommand<TransactionSummary> for InitializeValidator {
    fn command_name(&self) -> &'static str {
        "InitializeValidator"
    }

    async fn execute(mut self) -> CliTypedResult<TransactionSummary> {
        let operator_config = self.operator_config_file_args.load()?;
        let consensus_public_key = self
            .validator_consensus_key_args
            .get_consensus_public_key(&operator_config)?;
        let consensus_proof_of_possession = self
            .validator_consensus_key_args
            .get_consensus_proof_of_possession(&operator_config)?;
        let (
            validator_network_public_key,
            full_node_network_public_key,
            validator_host,
            full_node_host,
        ) = self
            .validator_network_addresses_args
            .get_network_configs(&operator_config)?;
        let validator_network_addresses =
            vec![validator_host.as_network_address(validator_network_public_key)?];
        let full_node_network_addresses =
            match (full_node_host.as_ref(), full_node_network_public_key) {
                (Some(host), Some(public_key)) => vec![host.as_network_address(public_key)?],
                (None, None) => vec![],
                _ => {
                    return Err(CliError::CommandArgumentError(
                        "If specifying fullnode addresses, both host and public key are required."
                            .to_string(),
                    ))
                },
            };

        self.txn_options
            .submit_transaction(aptos_stdlib::stake_initialize_validator(
                consensus_public_key.to_bytes().to_vec(),
                consensus_proof_of_possession.to_bytes().to_vec(),
                // BCS encode, so that we can hide the original type
                bcs::to_bytes(&validator_network_addresses)?,
                bcs::to_bytes(&full_node_network_addresses)?,
            ))
            .await
            .map(|inner| inner.into())
    }
}

/// Arguments used for operator of the staking pool
#[derive(Parser)]
pub struct OperatorArgs {
    #[clap(flatten)]
    pub(crate) pool_address_args: OptionalPoolAddressArgs,
}

impl OperatorArgs {
    fn address_fallback_to_profile(
        &self,
        profile_options: &ProfileOptions,
    ) -> CliTypedResult<AccountAddress> {
        if let Some(address) = self.pool_address_args.pool_address {
            Ok(address)
        } else {
            profile_options.account_address()
        }
    }

    fn address_fallback_to_txn(
        &self,
        transaction_options: &TransactionOptions,
    ) -> CliTypedResult<AccountAddress> {
        if let Some(address) = self.pool_address_args.pool_address {
            Ok(address)
        } else {
            transaction_options.sender_address()
        }
    }
}

/// Join the validator set after meeting staking requirements
///
/// Joining the validator set requires sufficient stake.  Once the transaction
/// succeeds, you will join the validator set in the next epoch.
#[derive(Parser)]
pub struct JoinValidatorSet {
    #[clap(flatten)]
    pub(crate) txn_options: TransactionOptions,
    #[clap(flatten)]
    pub(crate) operator_args: OperatorArgs,
}

#[async_trait]
impl CliCommand<TransactionSummary> for JoinValidatorSet {
    fn command_name(&self) -> &'static str {
        "JoinValidatorSet"
    }

    async fn execute(mut self) -> CliTypedResult<TransactionSummary> {
        let address = self
            .operator_args
            .address_fallback_to_txn(&self.txn_options)?;

        self.txn_options
            .submit_transaction(aptos_stdlib::stake_join_validator_set(address))
            .await
            .map(|inner| inner.into())
    }
}

/// Leave the validator set
///
/// Leaving the validator set will require you to have unlocked and withdrawn all stake.  After this
/// transaction is successful, you will leave the validator set in the next epoch.
#[derive(Parser)]
pub struct LeaveValidatorSet {
    #[clap(flatten)]
    pub(crate) txn_options: TransactionOptions,
    #[clap(flatten)]
    pub(crate) operator_args: OperatorArgs,
}

#[async_trait]
impl CliCommand<TransactionSummary> for LeaveValidatorSet {
    fn command_name(&self) -> &'static str {
        "LeaveValidatorSet"
    }

    async fn execute(mut self) -> CliTypedResult<TransactionSummary> {
        let address = self
            .operator_args
            .address_fallback_to_txn(&self.txn_options)?;

        self.txn_options
            .submit_transaction(aptos_stdlib::stake_leave_validator_set(address))
            .await
            .map(|inner| inner.into())
    }
}

/// Show validator stake information for a specific validator
///
/// This will show information about a specific validator, given its
/// `--pool-address`.
#[derive(Parser)]
pub struct ShowValidatorStake {
    #[clap(flatten)]
    pub(crate) profile_options: ProfileOptions,
    #[clap(flatten)]
    pub(crate) rest_options: RestOptions,
    #[clap(flatten)]
    pub(crate) operator_args: OperatorArgs,
}

#[async_trait]
impl CliCommand<serde_json::Value> for ShowValidatorStake {
    fn command_name(&self) -> &'static str {
        "ShowValidatorStake"
    }

    async fn execute(mut self) -> CliTypedResult<serde_json::Value> {
        let client = self.rest_options.client(&self.profile_options)?;
        let address = self
            .operator_args
            .address_fallback_to_profile(&self.profile_options)?;
        let response = client
            .get_resource(address, "0x1::stake::StakePool")
            .await?;
        Ok(response.into_inner())
    }
}

/// Show validator configuration for a specific validator
///
/// This will show information about a specific validator, given its
/// `--pool-address`.
#[derive(Parser)]
pub struct ShowValidatorConfig {
    #[clap(flatten)]
    pub(crate) profile_options: ProfileOptions,
    #[clap(flatten)]
    pub(crate) rest_options: RestOptions,
    #[clap(flatten)]
    pub(crate) operator_args: OperatorArgs,
}

#[async_trait]
impl CliCommand<ValidatorConfigSummary> for ShowValidatorConfig {
    fn command_name(&self) -> &'static str {
        "ShowValidatorConfig"
    }

    async fn execute(mut self) -> CliTypedResult<ValidatorConfigSummary> {
        let client = self.rest_options.client(&self.profile_options)?;
        let address = self
            .operator_args
            .address_fallback_to_profile(&self.profile_options)?;
        let validator_config: ValidatorConfig = client
            .get_account_resource_bcs(address, "0x1::stake::ValidatorConfig")
            .await?
            .into_inner();
        Ok((&validator_config)
            .try_into()
            .map_err(|err| CliError::BCS("Validator config", err))?)
    }
}

/// Show validator details of the validator set
///
/// This will show information about the validators including their voting power, addresses, and
/// public keys.
#[derive(Parser)]
pub struct ShowValidatorSet {
    #[clap(flatten)]
    pub(crate) profile_options: ProfileOptions,
    #[clap(flatten)]
    pub(crate) rest_options: RestOptions,
}

#[async_trait]
impl CliCommand<ValidatorSetSummary> for ShowValidatorSet {
    fn command_name(&self) -> &'static str {
        "ShowValidatorSet"
    }

    async fn execute(mut self) -> CliTypedResult<ValidatorSetSummary> {
        let client = self.rest_options.client(&self.profile_options)?;
        let validator_set: ValidatorSet = client
            .get_account_resource_bcs(CORE_CODE_ADDRESS, "0x1::stake::ValidatorSet")
            .await?
            .into_inner();

        ValidatorSetSummary::try_from(&validator_set)
            .map_err(|err| CliError::BCS("Validator Set", err))
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ValidatorSetSummary {
    pub scheme: ConsensusScheme,
    pub active_validators: Vec<ValidatorInfoSummary>,
    pub pending_inactive: Vec<ValidatorInfoSummary>,
    pub pending_active: Vec<ValidatorInfoSummary>,
    pub total_voting_power: u128,
    pub total_joining_power: u128,
}

impl TryFrom<&ValidatorSet> for ValidatorSetSummary {
    type Error = bcs::Error;

    fn try_from(set: &ValidatorSet) -> Result<Self, Self::Error> {
        Ok(ValidatorSetSummary {
            scheme: set.scheme,
            active_validators: set
                .active_validators
                .iter()
                .filter_map(|validator| validator.try_into().ok())
                .collect(),
            pending_inactive: set
                .pending_inactive
                .iter()
                .filter_map(|validator| validator.try_into().ok())
                .collect(),
            pending_active: set
                .pending_active
                .iter()
                .filter_map(|validator| validator.try_into().ok())
                .collect(),
            total_voting_power: set.total_voting_power,
            total_joining_power: set.total_joining_power,
        })
    }
}

impl From<&ValidatorSetSummary> for ValidatorSet {
    fn from(summary: &ValidatorSetSummary) -> Self {
        ValidatorSet {
            scheme: summary.scheme,
            active_validators: summary
                .active_validators
                .iter()
                .map(|validator| validator.into())
                .collect(),
            pending_inactive: summary
                .pending_inactive
                .iter()
                .map(|validator| validator.into())
                .collect(),
            pending_active: summary
                .pending_active
                .iter()
                .map(|validator| validator.into())
                .collect(),
            total_voting_power: summary.total_voting_power,
            total_joining_power: summary.total_joining_power,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ValidatorInfoSummary {
    // The validator's account address. AccountAddresses are initially derived from the account
    // auth pubkey; however, the auth key can be rotated, so one should not rely on this
    // initial property.
    pub account_address: AccountAddress,
    // Voting power of this validator
    consensus_voting_power: u64,
    // Validator config
    config: ValidatorConfigSummary,
}

impl TryFrom<&ValidatorInfo> for ValidatorInfoSummary {
    type Error = bcs::Error;

    fn try_from(info: &ValidatorInfo) -> Result<Self, Self::Error> {
        let config = info.config();
        let config = ValidatorConfig {
            consensus_public_key: config.consensus_public_key.to_bytes().to_vec(),
            validator_network_addresses: config.validator_network_addresses.clone(),
            fullnode_network_addresses: config.fullnode_network_addresses.clone(),
            validator_index: config.validator_index,
        };
        Ok(ValidatorInfoSummary {
            account_address: info.account_address,
            consensus_voting_power: info.consensus_voting_power(),
            config: ValidatorConfigSummary::try_from(&config)?,
        })
    }
}

impl From<&ValidatorInfoSummary> for ValidatorInfo {
    fn from(summary: &ValidatorInfoSummary) -> Self {
        let config = &summary.config;
        ValidatorInfo::new(
            summary.account_address,
            summary.consensus_voting_power,
            aptos_types::validator_config::ValidatorConfig::new(
                PublicKey::from_encoded_string(&config.consensus_public_key).unwrap(),
                bcs::to_bytes(&config.validator_network_addresses).unwrap(),
                bcs::to_bytes(&config.fullnode_network_addresses).unwrap(),
                config.validator_index,
            ),
        )
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Deserialize, Serialize)]
pub struct ValidatorConfig {
    pub consensus_public_key: Vec<u8>,
    pub validator_network_addresses: Vec<u8>,
    pub fullnode_network_addresses: Vec<u8>,
    pub validator_index: u64,
}

impl ValidatorConfig {
    pub fn new(
        consensus_public_key: Vec<u8>,
        validator_network_addresses: Vec<u8>,
        fullnode_network_addresses: Vec<u8>,
        validator_index: u64,
    ) -> Self {
        ValidatorConfig {
            consensus_public_key,
            validator_network_addresses,
            fullnode_network_addresses,
            validator_index,
        }
    }

    pub fn fullnode_network_addresses(&self) -> Result<Vec<NetworkAddress>, bcs::Error> {
        bcs::from_bytes(&self.fullnode_network_addresses)
    }

    pub fn validator_network_addresses(&self) -> Result<Vec<NetworkAddress>, bcs::Error> {
        bcs::from_bytes(&self.validator_network_addresses)
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ValidatorConfigSummary {
    pub consensus_public_key: String,
    /// This is an bcs serialized Vec<NetworkAddress>
    pub validator_network_addresses: Vec<NetworkAddress>,
    /// This is an bcs serialized Vec<NetworkAddress>
    pub fullnode_network_addresses: Vec<NetworkAddress>,
    pub validator_index: u64,
}

impl TryFrom<&ValidatorConfig> for ValidatorConfigSummary {
    type Error = bcs::Error;

    fn try_from(config: &ValidatorConfig) -> Result<Self, Self::Error> {
        let consensus_public_key = if config.consensus_public_key.is_empty() {
            "".into()
        } else {
            PublicKey::try_from(&config.consensus_public_key[..])
                .unwrap()
                .to_encoded_string()
                .unwrap()
        };
        Ok(ValidatorConfigSummary {
            consensus_public_key,
            // TODO: We should handle if some of these are not parsable
            validator_network_addresses: config.validator_network_addresses()?,
            fullnode_network_addresses: config.fullnode_network_addresses()?,
            validator_index: config.validator_index,
        })
    }
}

impl From<&ValidatorConfigSummary> for ValidatorConfig {
    fn from(summary: &ValidatorConfigSummary) -> Self {
        let consensus_public_key = if summary.consensus_public_key.is_empty() {
            vec![]
        } else {
            summary.consensus_public_key.as_bytes().to_vec()
        };
        ValidatorConfig {
            consensus_public_key,
            validator_network_addresses: bcs::to_bytes(&summary.validator_network_addresses)
                .unwrap(),
            fullnode_network_addresses: bcs::to_bytes(&summary.fullnode_network_addresses).unwrap(),
            validator_index: summary.validator_index,
        }
    }
}

// IMPORTANT (Vlad): changed max wait until faucet should start running
const MAX_WAIT_S: u64 = 1000;
const WAIT_INTERVAL_MS: u64 = 100;
const TESTNET_FOLDER: &str = "testnet";

/// Run local testnet
///
/// This local testnet will run it's own Genesis and run as a single node
/// network locally.  Optionally, a faucet can be added for minting APT coins.
// run-local-testnet --with-faucet --faucet-port 8081 --force-restart --assume-yes --evm-genesis-account 0x17C360CBfa39E218fB49CA754eC53af31684DD05
#[derive(Parser)]
pub struct RunLocalTestnet {
    /// An overridable config template for the test node
    ///
    /// If provided, the config will be used, and any needed configuration for the local testnet
    /// will override the config's values
    #[clap(long, parse(from_os_str))]
    config_path: Option<PathBuf>,

    /// The directory to save all files for the node
    ///
    /// Defaults to .aptos/testnet
    #[clap(long, parse(from_os_str))]
    test_dir: Option<PathBuf>,

    /// Random seed for key generation in test mode
    ///
    /// This allows you to have deterministic keys for testing
    #[clap(long, parse(try_from_str = FromHex::from_hex))]
    seed: Option<[u8; 32]>,

    /// Clean the state and start with a new chain at genesis
    ///
    /// This will wipe the aptosdb in `test-dir` to remove any incompatible changes, and start
    /// the chain fresh.  Note, that you will need to publish the module again and distribute funds
    /// from the faucet accordingly
    #[clap(long)]
    force_restart: bool,

    /// Run a faucet alongside the node
    ///
    /// Allows you to run a faucet alongside the node to create and fund accounts for testing
    #[clap(long)]
    with_faucet: bool,

    /// Port to run the faucet on
    ///
    /// When running, you'll be able to use the faucet at `http://localhost:<port>/mint` e.g.
    /// `http//localhost:8080/mint`
    #[clap(long, default_value = "8081")]
    faucet_port: u16,

    /// Disable the delegation of faucet minting to a dedicated account
    #[clap(long)]
    do_not_delegate: bool,

    #[clap(flatten)]
    prompt_options: PromptOptions,

    /// Specify the EVM address (in EVM format - 20 bytes) to send genesis tokens to
    #[clap(long)]
    evm_genesis_account: Option<EthAddress>,

    #[clap(long)]
    move_genesis_account: Option<AccountAddress>,
}

#[async_trait]
impl CliCommand<()> for RunLocalTestnet {
    fn command_name(&self) -> &'static str {
        "RunLocalTestnet"
    }

    async fn execute(mut self) -> CliTypedResult<()> {
        let rng = self
            .seed
            .map(StdRng::from_seed)
            .unwrap_or_else(StdRng::from_entropy);

        let global_config = GlobalConfig::load()?;
        let test_dir = global_config
            .get_config_location(ConfigSearchMode::CurrentDirAndParents)?
            .join(TESTNET_FOLDER);

        // Remove the current test directory and start with a new node
        if self.force_restart && test_dir.exists() {
            prompt_yes_with_override(
                "Are you sure you want to delete the existing chain?",
                self.prompt_options,
            )?;
            std::fs::remove_dir_all(test_dir.as_path()).map_err(|err| {
                CliError::IO(format!("Failed to delete {}", test_dir.display()), err)
            })?;
        }

        // Spawn the node in a separate thread
        let config_path = self.config_path.clone();
        let test_dir_copy = test_dir.clone();

        // for i in self.move_genesis_account.unwrap().into_iter() {
        //     println!("{i}");
        // }

        let node_thread_handle = thread::spawn(move || {
            let result = aptos_node::setup_test_environment_and_start_node(
                config_path,
                Some(test_dir_copy),
                false,
                false,
                aptos_cached_packages::head_release_bundle(),
                rng,
                self.evm_genesis_account,
                self.move_genesis_account,
            );
            eprintln!("Node stopped unexpectedly {:#?}", result);
        });

        // Run faucet if selected
        let maybe_faucet_future = if self.with_faucet {
            let max_wait = Duration::from_secs(MAX_WAIT_S);
            let wait_interval = Duration::from_millis(WAIT_INTERVAL_MS);

            // Load the config to get the rest port
            let config_path = test_dir.join("0").join("node.yaml");

            // We have to wait for the node to be configured above in the other thread
            let mut config = None;
            let start = Instant::now();
            while start.elapsed() < max_wait {
                if let Ok(loaded_config) = NodeConfig::load(&config_path) {
                    config = Some(loaded_config);
                    break;
                }
                tokio::time::sleep(wait_interval).await;
            }

            // Retrieve the port from the local node
            let port = if let Some(config) = config {
                config.api.address.port()
            } else {
                return Err(CliError::UnexpectedError(
                    "Failed to find node configuration to start faucet".to_string(),
                ));
            };

            // Check that the REST API is ready
            let rest_url = Url::parse(&format!("http://localhost:{}", port)).map_err(|err| {
                CliError::UnexpectedError(format!("Failed to parse localhost URL {}", err))
            })?;
            let rest_client = aptos_rest_client::Client::new(rest_url.clone());
            let start = Instant::now();
            let mut started_successfully = false;

            while start.elapsed() < max_wait {
                if rest_client.get_index().await.is_ok() {
                    started_successfully = true;
                    break;
                }
                tokio::time::sleep(wait_interval).await
            }

            if !started_successfully {
                return Err(CliError::UnexpectedError(
                    "Failed to startup local node before faucet".to_string(),
                ));
            }

            // Start the faucet
            Some(
                FaucetArgs {
                    address: "0.0.0.0".to_string(),
                    port: self.faucet_port,
                    server_url: rest_url,
                    mint_key_file_path: test_dir.join("mint.key"),
                    mint_key: None,
                    mint_account_address: None,
                    chain_id: ChainId::test(),
                    maximum_amount: None,
                    do_not_delegate: self.do_not_delegate,
                }
                .run(),
            )
        } else {
            None
        };

        // Collect futures that should never end.
        let mut futures: Vec<Pin<Box<dyn futures::Future<Output = ()> + Send>>> = Vec::new();

        // This future just waits for the node thread.
        let node_future = async move {
            loop {
                if node_thread_handle.is_finished() {
                    return;
                }
                tokio::time::sleep(Duration::from_millis(500)).await;
            }
        };

        // Wait for all the futures. We should never get past this point unless
        // something goes wrong or the user signals for the process to end.
        futures.push(Box::pin(node_future));
        if let Some(faucet_future) = maybe_faucet_future {
            futures.push(Box::pin(faucet_future));
        }
        futures::future::select_all(futures).await;

        Err(CliError::UnexpectedError(
            "One of the components stopped unexpectedly".to_string(),
        ))
    }
}

/// Update consensus key for the validator node
#[derive(Parser)]
pub struct UpdateConsensusKey {
    #[clap(flatten)]
    pub(crate) txn_options: TransactionOptions,
    #[clap(flatten)]
    pub(crate) operator_args: OperatorArgs,
    #[clap(flatten)]
    pub(crate) operator_config_file_args: OperatorConfigFileArgs,
    #[clap(flatten)]
    pub(crate) validator_consensus_key_args: ValidatorConsensusKeyArgs,
}

#[async_trait]
impl CliCommand<TransactionSummary> for UpdateConsensusKey {
    fn command_name(&self) -> &'static str {
        "UpdateConsensusKey"
    }

    async fn execute(mut self) -> CliTypedResult<TransactionSummary> {
        let address = self
            .operator_args
            .address_fallback_to_txn(&self.txn_options)?;

        let operator_config = self.operator_config_file_args.load()?;
        let consensus_public_key = self
            .validator_consensus_key_args
            .get_consensus_public_key(&operator_config)?;
        let consensus_proof_of_possession = self
            .validator_consensus_key_args
            .get_consensus_proof_of_possession(&operator_config)?;
        self.txn_options
            .submit_transaction(aptos_stdlib::stake_rotate_consensus_key(
                address,
                consensus_public_key.to_bytes().to_vec(),
                consensus_proof_of_possession.to_bytes().to_vec(),
            ))
            .await
            .map(|inner| inner.into())
    }
}

/// Update the current validator's network and fullnode network addresses
#[derive(Parser)]
pub struct UpdateValidatorNetworkAddresses {
    #[clap(flatten)]
    pub(crate) txn_options: TransactionOptions,
    #[clap(flatten)]
    pub(crate) operator_args: OperatorArgs,
    #[clap(flatten)]
    pub(crate) operator_config_file_args: OperatorConfigFileArgs,
    #[clap(flatten)]
    pub(crate) validator_network_addresses_args: ValidatorNetworkAddressesArgs,
}

#[async_trait]
impl CliCommand<TransactionSummary> for UpdateValidatorNetworkAddresses {
    fn command_name(&self) -> &'static str {
        "UpdateValidatorNetworkAddresses"
    }

    async fn execute(mut self) -> CliTypedResult<TransactionSummary> {
        let address = self
            .operator_args
            .address_fallback_to_txn(&self.txn_options)?;

        let validator_config = self.operator_config_file_args.load()?;
        let (
            validator_network_public_key,
            full_node_network_public_key,
            validator_host,
            full_node_host,
        ) = self
            .validator_network_addresses_args
            .get_network_configs(&validator_config)?;
        let validator_network_addresses =
            vec![validator_host.as_network_address(validator_network_public_key)?];
        let full_node_network_addresses =
            match (full_node_host.as_ref(), full_node_network_public_key) {
                (Some(host), Some(public_key)) => vec![host.as_network_address(public_key)?],
                (None, None) => vec![],
                _ => {
                    return Err(CliError::CommandArgumentError(
                        "If specifying fullnode addresses, both host and public key are required."
                            .to_string(),
                    ))
                },
            };

        self.txn_options
            .submit_transaction(aptos_stdlib::stake_update_network_and_fullnode_addresses(
                address,
                // BCS encode, so that we can hide the original type
                bcs::to_bytes(&validator_network_addresses)?,
                bcs::to_bytes(&full_node_network_addresses)?,
            ))
            .await
            .map(|inner| inner.into())
    }
}

/// Analyze the performance of one or more validators
#[derive(Parser)]
pub struct AnalyzeValidatorPerformance {
    /// First epoch to analyze
    ///
    /// Defaults to the first epoch
    #[clap(long, default_value = "-2")]
    pub start_epoch: i64,

    /// Last epoch to analyze
    ///
    /// Defaults to the latest epoch
    #[clap(long)]
    pub end_epoch: Option<i64>,

    /// Analyze mode for the validator: [All, DetailedEpochTable, ValidatorHealthOverTime, NetworkHealthOverTime]
    #[clap(arg_enum, long)]
    pub(crate) analyze_mode: AnalyzeMode,

    /// Filter of stake pool addresses to analyze
    ///
    /// Defaults to all stake pool addresses
    #[clap(long, multiple_values = true, parse(try_from_str=crate::common::types::load_account_arg))]
    pub pool_addresses: Vec<AccountAddress>,

    #[clap(flatten)]
    pub(crate) rest_options: RestOptions,
    #[clap(flatten)]
    pub(crate) profile_options: ProfileOptions,
}

#[derive(PartialEq, Eq, clap::ArgEnum, Clone)]
pub enum AnalyzeMode {
    /// Print all other modes simultaneously
    All,
    /// For each epoch, print a detailed table containing performance
    /// of each of the validators.
    DetailedEpochTable,
    /// For each validator, summarize it's performance in an epoch into
    /// one of the predefined reliability buckets,
    /// and prints it's performance across epochs.
    ValidatorHealthOverTime,
    /// For each epoch summarize how many validators were in
    /// each of the reliability buckets.
    NetworkHealthOverTime,
}

#[async_trait]
impl CliCommand<()> for AnalyzeValidatorPerformance {
    fn command_name(&self) -> &'static str {
        "AnalyzeValidatorPerformance"
    }

    async fn execute(mut self) -> CliTypedResult<()> {
        let client = self.rest_options.client(&self.profile_options)?;

        let epochs =
            FetchMetadata::fetch_new_block_events(&client, Some(self.start_epoch), self.end_epoch)
                .await?;
        let mut stats = HashMap::new();

        let print_detailed = self.analyze_mode == AnalyzeMode::DetailedEpochTable
            || self.analyze_mode == AnalyzeMode::All;
        for epoch_info in epochs {
            let mut epoch_stats =
                AnalyzeValidators::analyze(&epoch_info.blocks, &epoch_info.validators);
            if !self.pool_addresses.is_empty() {
                let mut filtered_stats: HashMap<AccountAddress, ValidatorStats> = HashMap::new();
                for pool_address in &self.pool_addresses {
                    filtered_stats.insert(
                        *pool_address,
                        *epoch_stats.validator_stats.get(pool_address).unwrap(),
                    );
                }
                epoch_stats.validator_stats = filtered_stats;
            }
            if print_detailed {
                println!(
                    "Detailed table for {}epoch {}:",
                    if epoch_info.partial { "partial " } else { "" },
                    epoch_info.epoch
                );
                AnalyzeValidators::print_detailed_epoch_table(
                    &epoch_stats,
                    Some((
                        "voting_power",
                        &epoch_info
                            .validators
                            .iter()
                            .map(|v| (v.address, v.voting_power.to_string()))
                            .collect::<HashMap<_, _>>(),
                    )),
                    true,
                );
            }
            if !epoch_info.partial {
                stats.insert(epoch_info.epoch, epoch_stats);
            }
        }

        if stats.is_empty() {
            println!("No data found for given input");
            return Ok(());
        }
        let total_stats = stats.values().cloned().reduce(|a, b| a + b).unwrap();
        if print_detailed {
            println!(
                "Detailed table for all epochs [{}, {}]:",
                stats.keys().min().unwrap(),
                stats.keys().max().unwrap()
            );
            AnalyzeValidators::print_detailed_epoch_table(&total_stats, None, true);
        }
        let all_validators: Vec<_> = total_stats.validator_stats.keys().cloned().collect();
        if self.analyze_mode == AnalyzeMode::ValidatorHealthOverTime
            || self.analyze_mode == AnalyzeMode::All
        {
            println!(
                "Validator health over epochs [{}, {}]:",
                stats.keys().min().unwrap(),
                stats.keys().max().unwrap()
            );
            AnalyzeValidators::print_validator_health_over_time(&stats, &all_validators, None);
        }
        if self.analyze_mode == AnalyzeMode::NetworkHealthOverTime
            || self.analyze_mode == AnalyzeMode::All
        {
            println!(
                "Network health over epochs [{}, {}]:",
                stats.keys().min().unwrap(),
                stats.keys().max().unwrap()
            );
            AnalyzeValidators::print_network_health_over_time(&stats, &all_validators);
        }
        Ok(())
    }
}

/// Bootstrap AptosDB from a backup
///
/// Enables users to load from a backup to catch their node's DB up to a known state.
#[derive(Parser)]
pub struct BootstrapDbFromBackup {
    /// Config file for the source backup
    ///
    /// This file configures if we should use local files or cloud storage, and how to access
    /// the backup.
    #[clap(long, parse(from_os_str))]
    config_path: PathBuf,

    /// Target database directory
    ///
    /// The directory to create the AptosDB with snapshots and transactions from the backup.
    /// The data folder can later be used to start an Aptos node. e.g. /opt/aptos/data/db
    #[clap(long = "target-db-dir", parse(from_os_str))]
    pub db_dir: PathBuf,

    #[clap(flatten)]
    pub metadata_cache_opt: MetadataCacheOpt,

    #[clap(flatten)]
    pub concurrent_downloads: ConcurrentDownloadsOpt,

    #[clap(flatten)]
    pub replay_concurrency_level: ReplayConcurrencyLevelOpt,
}

#[async_trait]
impl CliCommand<()> for BootstrapDbFromBackup {
    fn command_name(&self) -> &'static str {
        "BootstrapDbFromBackup"
    }

    async fn execute(self) -> CliTypedResult<()> {
        let opt = RestoreCoordinatorOpt {
            metadata_cache_opt: self.metadata_cache_opt,
            replay_all: false,
            ledger_history_start_version: None,
            skip_epoch_endings: false,
        };
        let global_opt = GlobalRestoreOpt {
            dry_run: false,
            db_dir: Some(self.db_dir),
            target_version: None,
            trusted_waypoints: Default::default(),
            rocksdb_opt: RocksdbOpt::default(),
            concurrent_downloads: self.concurrent_downloads,
            replay_concurrency_level: self.replay_concurrency_level,
        }
        .try_into()?;
        let storage = Arc::new(CommandAdapter::new(
            CommandAdapterConfig::load_from_file(&self.config_path).await?,
        ));

        // hack: get around this error, related to use of `async_trait`:
        //   error: higher-ranked lifetime error
        //   ...
        //   = note: could not prove for<'r, 's> Pin<Box<impl futures::Future<Output = std::result::Result<(), CliError>>>>: CoerceUnsized<Pin<Box<(dyn futures::Future<Output = std::result::Result<(), CliError>> + std::marker::Send + 's)>>>
        tokio::task::spawn_blocking(|| {
            let runtime = tokio::runtime::Runtime::new().unwrap();
            runtime.block_on(RestoreCoordinator::new(opt, global_opt, storage).run())
        })
        .await
        .unwrap()?;
        Ok(())
    }
}

/// Show Epoch information
///
/// Displays the current epoch, the epoch length, and the estimated time of the next epoch
#[derive(Parser)]
pub struct ShowEpochInfo {
    #[clap(flatten)]
    pub(crate) profile_options: ProfileOptions,
    #[clap(flatten)]
    pub(crate) rest_options: RestOptions,
}

#[async_trait]
impl CliCommand<EpochInfo> for ShowEpochInfo {
    fn command_name(&self) -> &'static str {
        "ShowEpochInfo"
    }

    async fn execute(self) -> CliTypedResult<EpochInfo> {
        let client = &self.rest_options.client(&self.profile_options)?;
        get_epoch_info(client).await
    }
}

async fn get_epoch_info(client: &Client) -> CliTypedResult<EpochInfo> {
    let (block_resource, state): (BlockResource, State) = client
        .get_account_resource_bcs(CORE_CODE_ADDRESS, "0x1::block::BlockResource")
        .await?
        .into_parts();
    let reconfig_resource: ConfigurationResource = client
        .get_account_resource_at_version_bcs(
            CORE_CODE_ADDRESS,
            "0x1::reconfiguration::Configuration",
            state.version,
        )
        .await?
        .into_inner();

    let epoch_interval = block_resource.epoch_interval();
    let epoch_interval_secs = epoch_interval / SECS_TO_MICROSECS;
    let last_reconfig = reconfig_resource.last_reconfiguration_time();
    Ok(EpochInfo {
        epoch: reconfig_resource.epoch(),
        epoch_interval_secs,
        current_epoch_start_time: Time::new_micros(last_reconfig),
        next_epoch_start_time: Time::new_micros(last_reconfig + epoch_interval),
    })
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EpochInfo {
    epoch: u64,
    epoch_interval_secs: u64,
    current_epoch_start_time: Time,
    next_epoch_start_time: Time,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Time {
    unix_time: u128,
    utc_time: DateTime<Utc>,
}

impl Time {
    pub fn new(time: Duration) -> Self {
        let date_time =
            NaiveDateTime::from_timestamp_opt(time.as_secs() as i64, time.subsec_nanos())
                .expect("invalid or out-of-range datetime");
        let utc_time = DateTime::from_utc(date_time, Utc);
        // TODO: Allow configurable time zone
        Self {
            unix_time: time.as_micros(),
            utc_time,
        }
    }

    pub fn new_micros(microseconds: u64) -> Self {
        Self::new(Duration::from_micros(microseconds))
    }

    pub fn new_seconds(seconds: u64) -> Self {
        Self::new(Duration::from_secs(seconds))
    }
}
