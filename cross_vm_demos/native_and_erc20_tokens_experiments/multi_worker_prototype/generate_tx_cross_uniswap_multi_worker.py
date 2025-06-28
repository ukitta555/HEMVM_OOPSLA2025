import asyncio
import random

import concurrent
from eth_typing import Address
from hexbytes import HexBytes
from web3 import Web3

from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag
from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument


from funding_utils_local import approve_eth_custom_coin, fund_npc_accounts_custom_coin_aptos, fund_npc_accounts_custom_coin_eth, fund_npc_accounts_native_coin_aptos, fund_npc_accounts_native_coin_eth, register_lp_tokens_uniswap_cross_experiment, register_mirror_eth_coin, transfer_move_custom_coin_cross_space

from utils import LIDLAptosSDK, TxType, cache_of_eth_addresses, cache_of_move_accounts, eth_sign_tx_dynamic_pk, read_eth_keys, read_move_keys, write_tx_to_file_with_tx_type


K = 1000
num_of_txs = 500 * K


async def main():
    await fund_npc_accounts_native_coin_eth(
        eth_keys_path="../../experiment_runner/keys/private_keys_ethereum.txt"
    )
    await fund_npc_accounts_native_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt"
    )
    await fund_npc_accounts_custom_coin_eth(
        eth_keys_path="../../experiment_runner/keys/private_keys_ethereum.txt",
        only_eth_coin_deployed=False,
        erc_20_cross_setup=True
    )
    await fund_npc_accounts_custom_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt",
        erc_20_cross_setup=True
    )

    eth_private_keys = read_eth_keys()
    move_private_keys = read_move_keys()
    eth_addresses = cache_of_eth_addresses(eth_private_keys=eth_private_keys)
    move_accounts = cache_of_move_accounts(move_private_keys=move_private_keys)
    

    deployer_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
    cross_uniswap_wrapper_address = bytes.fromhex("812cBBdE09AF8214a5c3addE18Fcec9891196494")

    payload = EntryFunction.natural(
        f"{deployer_address}::cross_vm_coin_reverse_demo",
        "swap_exact_tokens_for_tokens",
        [
            TypeTag(StructTag.from_str(f"{deployer_address}::native_coin::DiemCoin")),
            TypeTag(StructTag.from_str(f"{deployer_address}::mirror_coin::EthCoin"))
        ],
        [
            TransactionArgument(10 ** 5, Serializer.u64),
            TransactionArgument(1, Serializer.u64),
            TransactionArgument(1913334000, Serializer.u64),
            TransactionArgument(cross_uniswap_wrapper_address, Serializer.to_bytes)
        ],
    )

    sdk = LIDLAptosSDK()
    
    with open(f"./transaction_batches/uniswap_cross_multiworker_{num_of_txs // K}k.txt", "wb") as f:
        for idx in range(num_of_txs):
            sender_pk = random.choice(move_private_keys)
            sender_account = move_accounts[sender_pk]
            
            signed_tx: SignedTransaction = sdk.create_bcs_signed_transaction(sender_account, TransactionPayload(payload))
            write_tx_to_file_with_tx_type(file=f, unsent_signed_txn=signed_tx, tx_type=TxType.CROSS_APTOS_TX)

            if idx % 1000 == 0:
                print(f"Txs generation progress: {idx * 100 / num_of_txs}%")

if __name__ == "__main__":
    asyncio.run(main())