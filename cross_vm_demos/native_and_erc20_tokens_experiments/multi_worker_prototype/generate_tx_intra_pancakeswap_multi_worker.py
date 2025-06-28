from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag


from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument
import asyncio
import random

from funding_utils_local import approve_eth_custom_coin, fund_npc_accounts_custom_coin_aptos, fund_npc_accounts_custom_coin_eth, fund_npc_accounts_native_coin_aptos, fund_npc_accounts_native_coin_eth, register_custom_coin_pancakeswap_native, register_lp_tokens_uniswap_cross_experiment, register_mirror_eth_coin, transfer_move_custom_coin_cross_space

from utils import LIDLAptosSDK, TxType, cache_of_eth_addresses, cache_of_move_accounts, eth_sign_tx_dynamic_pk, read_eth_keys, read_move_keys, write_tx_to_file_with_tx_type

K = 1000
num_of_txs = 500 * K


async def main():
    # await fund_npc_accounts_native_coin_eth(
    #     eth_keys_path="../../experiment_runner/keys/private_keys_ethereum.txt"
    # )
    await fund_npc_accounts_native_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt"
    )
    # await fund_npc_accounts_custom_coin_eth(
    #     eth_keys_path="../../experiment_runner/keys/private_keys_ethereum.txt",
    #     only_eth_coin_deployed=False,
    #     erc_20_cross_setup=True
    # )
    await fund_npc_accounts_custom_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt",
        erc_20_cross_setup=True
    )
    await register_custom_coin_pancakeswap_native(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt",
    )

    move_private_keys = read_move_keys()
    move_accounts = cache_of_move_accounts(move_private_keys=move_private_keys)
    

    deployer_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
    router_address = "0x7a526ec5f06a7976caec96614f0db691f53b452424a3897a18a115ddd300c110"

    payload = EntryFunction.natural(
        f"{router_address}::router",
        "swap_exact_input",
        [
            TypeTag(StructTag.from_str(f"{deployer_address}::native_coin::DiemCoin")),
            TypeTag(StructTag.from_str(f"{deployer_address}::native_coin_2::DiemCoin2"))
        ],
        [
            TransactionArgument(10 ** 5, Serializer.u64),
            TransactionArgument(1, Serializer.u64),
        ],
    )

    sdk = LIDLAptosSDK()
    
    with open(f"./transaction_batches/pancakeswap_intra_multiworker_{num_of_txs // K}k.txt", "wb") as f:
        for idx in range(num_of_txs):
            sender_pk = random.choice(move_private_keys)
            sender_account = move_accounts[sender_pk]
            
            signed_tx: SignedTransaction = sdk.create_bcs_signed_transaction(sender_account, TransactionPayload(payload))
            write_tx_to_file_with_tx_type(file=f, unsent_signed_txn=signed_tx, tx_type=TxType.NATIVE_APTOS_TX)

            if idx % 1000 == 0:
                print(f"Txs generation progress: {idx * 100 / num_of_txs}%")

if __name__ == "__main__":
    asyncio.run(main())

