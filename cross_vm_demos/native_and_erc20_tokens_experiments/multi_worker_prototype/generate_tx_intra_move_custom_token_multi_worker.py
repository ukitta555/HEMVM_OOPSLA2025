

import asyncio
import random
import sys

from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag 
from utils import LIDLAptosSDK, TxType, read_move_keys, write_tx_to_file_with_tx_type
from funding_utils_local import fund_npc_accounts_custom_coin_aptos, fund_npc_accounts_native_coin_aptos
# from move_scripts.balance_of import get_balance

from aptos_sdk.async_client import FaucetClient, RestClient
from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument


account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"

K = 1000
num_of_txs = 500 * K

# TODO: automatically run the node + deployment script to automate tx generation completely?
# potentially could use a strategy pattern to reduce boilerplate? generate() method will be the one doing all the work depending on the strategy
async def main():
    await fund_npc_accounts_native_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt"
    )
    await fund_npc_accounts_custom_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt",
        erc_20_cross_setup=False
    )

    move_private_keys = read_move_keys()

    sdk = LIDLAptosSDK()

  
    with open(f"./transaction_batches/move_custom_token_intra_{num_of_txs // K}k.txt", "wb") as file:
        print("Writing native txs...")
        for _ in range(0, num_of_txs):
            sender_pk = random.choice(move_private_keys)
            receiver_pk = sender_pk
            while receiver_pk == sender_pk:
                receiver_pk = random.choice(move_private_keys)
            
            sender_move = Account.load_key(sender_pk)
            receiver_move_intra = Account.load_key(receiver_pk)

            transaction_arguments = [
                TransactionArgument(receiver_move_intra.address(), Serializer.struct),
                TransactionArgument(10**2, Serializer.u64),
            ]

            payload = EntryFunction.natural(
                f"{account_address}::native_coin",
                "transfer",
                [],
                transaction_arguments,
            )

            tx_native: SignedTransaction = sdk.create_bcs_signed_transaction(sender_move, TransactionPayload(payload))
            write_tx_to_file_with_tx_type(file, tx_native, TxType.NATIVE_APTOS_TX)

if __name__ == "__main__":
    asyncio.run(main())

