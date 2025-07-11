// Copyright (c) Aptos
// SPDX-License-Identifier: Apache-2.0

use crate::{
    counters,
    epoch_manager::EpochManager,
    network::NetworkTask,
    network_interface::{ConsensusMsg, ConsensusNetworkClient, DIRECT_SEND, RPC},
    persistent_liveness_storage::StorageWriteProxy,
    state_computer::ExecutionProxy,
    txn_notifier::MempoolNotifier,
    util::time_service::ClockTimeService,
};
use aptos_config::{config::NodeConfig, network_id::NetworkId};
use aptos_consensus_notifications::ConsensusNotificationSender;
use aptos_event_notifications::ReconfigNotificationListener;
use aptos_executor::block_executor::BlockExecutor;
use aptos_logger::prelude::*;
use aptos_mempool::QuorumStoreRequest;
use aptos_network::{
    application::{interface::NetworkClient, storage::PeerMetadataStorage},
    protocols::network::{NetworkEvents, NetworkSender},
};
use aptos_storage_interface::DbReaderWriter;
use aptos_block_executor::aptos_vm::AptosVM;
use futures::channel::mpsc;
use std::{collections::HashMap, sync::Arc};
use tokio::runtime::Runtime;

/// Helper function to start consensus based on configuration and return the runtime
pub fn start_consensus(
    node_config: &NodeConfig,
    network_senders: HashMap<NetworkId, NetworkSender<ConsensusMsg>>,
    network_events: NetworkEvents<ConsensusMsg>,
    state_sync_notifier: Arc<dyn ConsensusNotificationSender>,
    consensus_to_mempool_sender: mpsc::Sender<QuorumStoreRequest>,
    aptos_db: DbReaderWriter,
    reconfig_events: ReconfigNotificationListener,
    peer_metadata_storage: Arc<PeerMetadataStorage>,
    benchmark_mutex: Arc<tokio::sync::Mutex<()>>
) -> Runtime {
    let runtime = aptos_runtimes::spawn_named_runtime("consensus".into(), None);
    let storage = Arc::new(StorageWriteProxy::new(node_config, aptos_db.reader.clone()));
    let txn_notifier = Arc::new(MempoolNotifier::new(
        consensus_to_mempool_sender.clone(),
        node_config.consensus.mempool_executed_txn_timeout_ms,
    ));

    // Important (Vlad): creation of the execution environment
    // Create execution threads HERE!
    let state_computer = Arc::new(ExecutionProxy::new(
        Arc::new(BlockExecutor::<AptosVM>::new(aptos_db)),
        txn_notifier,
        state_sync_notifier,
        runtime.handle(),
        benchmark_mutex
    ));

    let time_service = Arc::new(ClockTimeService::new(runtime.handle().clone()));

    let (timeout_sender, timeout_receiver) =
        aptos_channels::new(1_024, &counters::PENDING_ROUND_TIMEOUTS);
    let (self_sender, self_receiver) = aptos_channels::new(1_024, &counters::PENDING_SELF_MESSAGES);
    let network_client = NetworkClient::new(
        DIRECT_SEND.into(),
        RPC.into(),
        network_senders,
        peer_metadata_storage,
    );
    let consensus_network_client = ConsensusNetworkClient::new(network_client);

    let epoch_mgr = EpochManager::new(
        node_config,
        time_service,
        self_sender,
        consensus_network_client,
        timeout_sender,
        consensus_to_mempool_sender,
        state_computer,
        storage,
        reconfig_events,
    );

    let (network_task, network_receiver) = NetworkTask::new(network_events, self_receiver);

    runtime.spawn(network_task.start());
    runtime.spawn(epoch_mgr.start(timeout_receiver, network_receiver));

    debug!("Consensus started.");
    runtime
}
