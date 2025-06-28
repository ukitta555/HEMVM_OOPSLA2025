

import asyncio
from funding_utils_local import fund_npc_accounts_native_coin_aptos, fund_npc_accounts_native_coin_eth
import random
from time import perf_counter
from aptos_sdk.account import Account
from web3 import Web3
from utils import LIDLAptosSDK, TxType, decode_eth_private_key_to_address, eth_sign_tx_dynamic_pk, write_tx_to_file_with_tx_type
from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag
from aptos_sdk.account import Account


w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

K = 1000
num_of_txs = 500 * K

def sign_eth_native_transfer_tx(
        sender: str,
        receiver: str,
        current_txs: int,
        sender_pk: str
):
    unsent_txn = {
        'from': sender,
        'chainId': 129,
        'to': receiver,
        'value': 1 * 10**10,
        'nonce': current_txs,
        'gas': 21001,
        'gasPrice': 10 ** 9 + 1,
    }

    # print(f"Generated ETH transfer tx with nonce {current_txs}")
    return eth_sign_tx_dynamic_pk(
        w3=w3, 
        unsent_tx=unsent_txn, 
        sender_pk=sender_pk
    ) 


async def generate_txs():
    await fund_npc_accounts_native_coin_eth(
        eth_keys_path="../../experiment_runner/keys/private_keys_ethereum.txt"
    )

    await fund_npc_accounts_native_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt",
    )

    eth_private_keys = None
    move_private_keys = None
    eth_nonces = dict()
    eth_addresses = dict()
    move_accounts = dict()
    
    with open("./../../experiment_runner/keys/private_keys_aptos.txt", "r") as aptos_pk_file:
        move_private_keys = list(map(lambda x: x.strip(), aptos_pk_file.readlines()))
    
    with open("./../../experiment_runner/keys/private_keys_ethereum.txt", "r") as eth_pk_file:
        eth_private_keys = list(map(lambda x: x.strip(), eth_pk_file.readlines()))

    print(f"Number of private keys for Aptos side: {len(move_private_keys)}")
    print(f"Number of private keys for Ethereum side: {len(eth_private_keys)}")

    account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"

    sdk = LIDLAptosSDK() # custom sdk to create transactions with sequential nonces inside the script
    
    for eth_key in eth_private_keys:
        eth_addresses[eth_key] = decode_eth_private_key_to_address(eth_key)
    
    for move_key in move_private_keys:
        move_accounts[move_key] = Account.load_key(move_key)

    def move_intra_case(coin: float):
        return 0 <= coin < 0.2 

    def eth_intra_case(coin: float):
        return 0.2 <= coin < 1

    # never happens
    def move_cross_case(coin: float):
        return coin > 1

    # never happens
    def eth_cross_case(coin: float):
        return coin > 1

    with open(f"./transaction_batches/salad_native_coin_e80_m20_{num_of_txs // K}k.txt", "wb") as f:
        for _ in range(0, num_of_txs):
            salad_random_coin = random.uniform(0, 1)
            if move_intra_case(salad_random_coin):
                
                sender_pk = random.choice(move_private_keys)
                receiver_pk = sender_pk
                while receiver_pk == sender_pk:
                    receiver_pk = random.choice(move_private_keys)

                sender_move = move_accounts[sender_pk]
                receiver_move_intra = move_accounts[receiver_pk]

                # print(f"Move intra case, chosen accounts with PKs {sender_move.address()} -> {receiver_move_intra.address()}")
                
                transaction_arguments = [
                    TransactionArgument(receiver_move_intra.address(), Serializer.struct),
                    TransactionArgument(10**4, Serializer.u64),
                ]

                payload = EntryFunction.natural(
                    "0x1::coin",
                    "transfer",
                    [TypeTag(StructTag.from_str(f"0x1::aptos_coin::AptosCoin"))],
                    transaction_arguments,
                )

                tx: SignedTransaction = sdk.create_bcs_signed_transaction(sender_move, TransactionPayload(payload))
                write_tx_to_file_with_tx_type(
                    file=f, 
                    unsent_signed_txn=tx, 
                    tx_type=TxType.NATIVE_APTOS_TX
                )
            elif eth_intra_case(salad_random_coin):
                sender_pk = random.choice(eth_private_keys)
                receiver_pk = sender_pk
                while receiver_pk == sender_pk:
                    receiver_pk = random.choice(eth_private_keys)
                
                sender_eth = eth_addresses[sender_pk]
                receiver_eth_native = eth_addresses[receiver_pk]

                # print(f"Eth intra case, chosen accounts with PKs {sender_eth} -> {receiver_eth_native}")
                eth_nonces[sender_eth] = eth_nonces.get(sender_eth, 0)
                # print(sender_eth, eth_nonces[sender_eth])

                signed_tx = sign_eth_native_transfer_tx(
                    sender=sender_eth,
                    receiver=receiver_eth_native,
                    current_txs=eth_nonces[sender_eth],
                    sender_pk=sender_pk
                )
                write_tx_to_file_with_tx_type(
                    file=f, 
                    unsent_signed_txn=signed_tx, 
                    tx_type=TxType.NATIVE_ETH_TX
                )
                eth_nonces[sender_eth] += 1


if __name__ == "__main__":
    t1_start = perf_counter()
    asyncio.run(generate_txs())
    t1_stop = perf_counter()
    print("Elapsed time during the whole program in seconds:", t1_stop - t1_start)