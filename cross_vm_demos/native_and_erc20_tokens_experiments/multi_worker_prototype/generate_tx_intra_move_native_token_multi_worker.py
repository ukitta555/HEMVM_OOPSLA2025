

from funding_utils_local import fund_npc_accounts_native_coin_aptos
import asyncio
import random
import sys

from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag
from utils import LIDLAptosSDK, TxType, read_eth_keys, read_move_keys, write_tx_to_file_with_tx_type

from aptos_sdk.async_client import FaucetClient, RestClient
from utils import aptos_write_tx_to_file_no_padding

from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument

K = 1000
num_of_txs = 500 * K

async def main():
    await fund_npc_accounts_native_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt"
    )

    move_private_keys = read_move_keys()

    sdk = LIDLAptosSDK()

    with open(f"transaction_batches/move_native_token_intra_{num_of_txs // K}k.txt", "wb") as file:
        print("Writing txs...")
        for _ in range(0, num_of_txs):
            sender_pk = random.choice(move_private_keys)
            receiver_pk = sender_pk
            while receiver_pk == sender_pk:
                receiver_pk = random.choice(move_private_keys)

            sender_move = Account.load_key(sender_pk)
            receiver_move_intra = Account.load_key(receiver_pk)

            # print(f"Move intra case, chosen accounts with PKs {sender_move.address()} -> {receiver_move_intra.address()}")
            
            transaction_arguments = [
                TransactionArgument(receiver_move_intra.address(), Serializer.struct),
                TransactionArgument(10**2, Serializer.u64),
            ]

            payload = EntryFunction.natural(
                "0x1::coin",
                "transfer",
                [TypeTag(StructTag.from_str(f"0x1::aptos_coin::AptosCoin"))],
                transaction_arguments,
            )

            tx: SignedTransaction = sdk.create_bcs_signed_transaction(sender_move, TransactionPayload(payload))
            write_tx_to_file_with_tx_type(
                file=file, 
                unsent_signed_txn=tx, 
                tx_type=TxType.NATIVE_APTOS_TX
            )



if __name__ == "__main__":
    asyncio.run(main())