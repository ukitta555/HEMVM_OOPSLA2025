
import asyncio
import concurrent
import random
from time import perf_counter
from typing import BinaryIO
from eth_typing import Address
from hexbytes import HexBytes
from web3 import Web3

from funding_utils_local import fund_npc_accounts_native_coin_eth
from utils import TxType, decode_eth_private_key_to_address, eth_sign_tx_dynamic_pk, eth_sign_tx_genesis, read_eth_keys, write_tx_to_file_with_tx_type

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

K = 1000
num_of_txs = 500 * K

def sign_native_transfer_tx(tx_and_pk: tuple[dict, str]):
    unsent_txn, sender_pk = tx_and_pk
    print(f"Generated ETH transfer tx with nonce {unsent_txn['nonce']} for address {decode_eth_private_key_to_address(sender_pk)}")
    signed_tx = eth_sign_tx_dynamic_pk(w3, unsent_txn, sender_pk=sender_pk)
    return unsent_txn["nonce"], signed_tx


async def generate_and_write_swap_txs_parallel(f, public_address_of_senders_account):
    await fund_npc_accounts_native_coin_eth(
        eth_keys_path="../../experiment_runner/keys/private_keys_ethereum.txt"
    )
    eth_private_keys = read_eth_keys()
    eth_nonces = dict()
    addresses = dict()
    for key in eth_private_keys:
        addresses[key] = decode_eth_private_key_to_address(key)

    t1_start = perf_counter()
    unsigned_txs = []

    for idx in range(num_of_txs):
        sender_pk = random.choice(eth_private_keys)
        receiver_pk = sender_pk
        while receiver_pk == sender_pk:
            receiver_pk = random.choice(eth_private_keys)
        
        sender_eth = addresses[sender_pk]
        receiver_eth = addresses[receiver_pk]

        if eth_nonces.get(sender_eth) is None:
            eth_nonces[sender_eth] = 0

        unsent_txn = {
            'from': sender_eth,
            'chainId': 129,
            'to': receiver_eth,
            'value': 10**10,
            'nonce': eth_nonces[sender_eth],
            'gas': 21001,
            'gasPrice': 10 ** 9 + 1,
        }

        eth_nonces[sender_eth] += 1
        unsigned_txs.append((unsent_txn, sender_pk))
        if idx % 1000 == 0:
            print(f"Txs generation progress: {idx * 100 / num_of_txs}%")
    t1_stop = perf_counter()
    print("Elapsed time during the unsigned transaction generation in seconds:", t1_stop - t1_start)

    t1_start = perf_counter()
    with concurrent.futures.ProcessPoolExecutor(12) as executor:
        # weird Python shenanigans - PPE deadlocks on large arrays, most likely problems with clogged pipes between processes
        result_1: list[int, dict] = list(executor.map(sign_native_transfer_tx, unsigned_txs[0:100000]))
        result_2: list[int, dict] = list(executor.map(sign_native_transfer_tx, unsigned_txs[100000:200000]))
        result_3: list[int, dict] = list(executor.map(sign_native_transfer_tx, unsigned_txs[200000:300000]))
        result_4: list[int, dict] = list(executor.map(sign_native_transfer_tx, unsigned_txs[300000:400000]))
        result_5: list[int, dict] = list(executor.map(sign_native_transfer_tx, unsigned_txs[400000:500000]))
        result = result_1 + result_2 + result_3 + result_4 + result_5
        result.sort(key=lambda x: x[0])
        for (_, signed_tx) in result:
            write_tx_to_file_with_tx_type(file=f, unsent_signed_txn=signed_tx, tx_type=TxType.NATIVE_ETH_TX)
    t1_stop = perf_counter()
    print("Elapsed time during the signing and sorting phase in seconds:", t1_stop - t1_start)

async def generate_txs():
    sender = "0x14Dcb427A216216791fB63973c5b13878de30916"
    with open(f"./transaction_batches/eth_native_token_intra_multiworker_{num_of_txs // K}k.txt", "wb") as f:
        await generate_and_write_swap_txs_parallel(f, sender)

if __name__ == "__main__":
    asyncio.run(generate_txs())