use aptos_api_types::HexEncodedBytes;
use cfx_evm::{contract_address, vm::CreateContractAddress};
use cfx_primitives::{transaction::eip155_signature, Action, SignedTransaction as EthTransaction};
use ethereum_types::{H160, H256, H512, U256, U64};
use rlp::Encodable;
use serde::{Deserialize, Serialize};

/// Transaction
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Transaction {
    // /// transaction type
    // #[serde(rename = "type", skip_serializing_if = "Option::is_none")]
    // pub transaction_type: Option<U64>,
    /// Hash
    pub hash: H256,
    /// Nonce
    pub nonce: U256,
    /// Block hash
    pub block_hash: Option<H256>,
    /// Block number
    pub block_number: Option<U256>,
    /// Transaction Index
    pub transaction_index: Option<U256>,
    /// Sender
    pub from: H160,
    /// Recipient
    pub to: Option<H160>,
    /// Transfered value
    pub value: U256,
    /// Gas Price
    pub gas_price: U256,
    /// Max fee per gas
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_fee_per_gas: Option<U256>,
    /// Gas
    pub gas: U256,
    /// Data
    pub input: HexEncodedBytes,
    /// Creates contract
    pub creates: Option<H160>,
    /// Raw transaction data
    pub raw: HexEncodedBytes,
    /// Public key of the signer.
    pub public_key: Option<H512>,
    /// The network id of the transaction, if any.
    pub chain_id: Option<U64>,
    /// The standardised V field of the signature (0 or 1). Used by legacy
    /// transaction
    #[serde(skip_serializing_if = "Option::is_none")]
    pub standard_v: Option<U256>,
    /// The standardised V field of the signature.
    pub v: U256,
    /// The R field of the signature.
    pub r: U256,
    /// The S field of the signature.
    pub s: U256,
    // Whether tx is success
    pub status: Option<U64>,
    /* /// Transaction activates at specified block.
     * pub condition: Option<TransactionCondition>,
     * /// optional access list
     * #[serde(skip_serializing_if = "Option::is_none")]
     * pub access_list: Option<AccessList>,
     * /// miner bribe
     * #[serde(skip_serializing_if = "Option::is_none")]
     * pub max_priority_fee_per_gas: Option<U256>, */
}

impl Transaction {
    #[allow(unused)]
    /// Convert `SignedTransaction` into RPC Transaction.
    pub fn from_signed(
        t: &EthTransaction,
        block_info: (Option<H256>, Option<U256>, Option<U256>),
        exec_info: (Option<U64>, Option<H160>),
    ) -> Transaction {
        let signature = t.signature();
        // We only support EIP-155
        // let access_list = match t.as_unsigned() {
        //     TypedTransaction::AccessList(tx) => {
        //         Some(tx.access_list.clone().into_iter().map(Into::into).
        // collect())     }
        //     TypedTransaction::EIP1559Transaction(tx) => Some(
        //         tx.transaction
        //             .access_list
        //             .clone()
        //             .into_iter()
        //             .map(Into::into)
        //             .collect(),
        //     ),
        //     TypedTransaction::Legacy(_) => None,
        // };

        Transaction {
            hash: t.hash(),
            nonce: *t.nonce(),
            block_hash: block_info.0,
            block_number: block_info.1,
            transaction_index: block_info.2,
            from: t.sender().address,
            to: match t.action() {
                Action::Create => None,
                Action::Call(ref address) => Some(*address),
            },
            value: *t.value(),
            gas_price: *t.gas_price(),
            max_fee_per_gas: None,
            gas: *t.gas(),
            input: t.data().clone().into(),
            creates: exec_info.1,
            raw: t.transaction.transaction.rlp_bytes().to_vec().into(),
            public_key: t.public().map(Into::into),
            chain_id: t.chain_id().map(|x| U64::from(x as u64)),
            standard_v: Some(signature.v().into()),
            v: eip155_signature::add_chain_replay_protection(
                signature.v(),
                t.chain_id().map(|x| x as u64),
            )
            .into(), /* The protected EIP155 v */
            r: signature.r().into(),
            s: signature.s().into(),
            status: exec_info.0,
        }
    }
}

pub fn deployed_contract_address(t: &EthTransaction) -> Option<H160> {
    match t.action() {
        Action::Create => {
            let (new_contract_address, _) = contract_address(
                CreateContractAddress::FromSenderNonce,
                0.into(),
                &t.sender(),
                t.nonce(),
                t.data(),
            );
            Some(new_contract_address.address)
        },
        Action::Call(_) => None,
    }
}
