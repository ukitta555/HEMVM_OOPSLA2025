
import asyncio
import random

from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag
from funding_utils_local import fund_npc_accounts_custom_coin_aptos, fund_npc_accounts_native_coin_aptos
from utils import LIDLAptosSDK, TxType, decode_eth_private_key_to_address, read_eth_keys, read_move_keys, write_tx_to_file_with_tx_type
from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument


K = 1000
num_of_txs = 500 * K



async def main():
    await fund_npc_accounts_native_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt"
    )

    await fund_npc_accounts_custom_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt",
        erc_20_cross_setup=True
    )

    move_private_keys = read_move_keys()
    eth_private_keys = read_eth_keys()  

    account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
    sdk = LIDLAptosSDK() # custom sdk to create transactions with sequential nonces inside the script

    with open(f"./transaction_batches/move_custom_token_cross_multiworker_{num_of_txs // K}k.txt", "wb") as file:
        for _ in range(0, num_of_txs):            
            sender_pk = random.choice(move_private_keys)
            receiver_pk = random.choice(eth_private_keys)

            sender_move = Account.load_key(sender_pk)
            receiver_eth_cross = bytes.fromhex(decode_eth_private_key_to_address(receiver_pk)[2:])

            # print(f"Move cross, chosen accounts with PKs {sender_move.address()} -> {decode_eth_private_key_to_address(receiver_pk)[2:]}")
            transaction_arguments = [
                TransactionArgument(receiver_eth_cross, Serializer.to_bytes),
                TransactionArgument(10 ** 4, Serializer.u64),
            ]

            payload = EntryFunction.natural(
                f"{account_address}::cross_vm_coin_erc20",
                "deposit",
                [TypeTag(StructTag.from_str(f"{account_address}::native_coin::DiemCoin"))],
                transaction_arguments,
            )

            tx_cross: SignedTransaction = sdk.create_bcs_signed_transaction(sender_move, TransactionPayload(payload))
            write_tx_to_file_with_tx_type(
                file=file, 
                unsent_signed_txn=tx_cross, 
                tx_type=TxType.CROSS_APTOS_TX
            )

if __name__ == "__main__":
    asyncio.run(main())

