import concurrent
from time import perf_counter

from eth_typing import Address
from hexbytes import HexBytes
from web3 import Web3
from abis import vault_abi
from utils import eth_sign_tx

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

num_of_txs = 10 ** 5

#  (String) Vault address
#  (Hex) 0x7d3d6e9f5ab582112c5cdbd712e808b2a4eafa5d
#  (String) Mirror address
#  (Hex) 0x5ca0f43868e106ac9aec48f8f1285896c0b9865d

def generate_cross_transfer_tx(nonce: int):
    VaultERC20 = w3.eth.contract(
        address=Address(HexBytes("0x7d3d6e9f5ab582112c5cdbd712e808b2a4eafa5d")),
        abi=vault_abi
    )
    sender = "0x14Dcb427A216216791fB63973c5b13878de30916"
    receiver = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"

    unsent_txn = VaultERC20.functions.deposit(
        HexBytes(receiver),
        10**10
    ).build_transaction(
        {
            "from": sender,
            'value': 0,
            'gas': 3000000,
            'gasPrice': 10 ** 13 + 1,
            "nonce": nonce,
        }
    )
    print(f"Generated deposit tx with nonce {nonce}")
    signed_tx = eth_sign_tx(w3, unsent_txn)
    return nonce, signed_tx

def generate_txs():
    sender = "0x14Dcb427A216216791fB63973c5b13878de30916"
    with open("./transaction_batches/eth_coin_cross_100k.txt", "wb") as f:
        generate_and_write_swap_txs_parallel(f, sender)


def generate_and_write_swap_txs_parallel(f, public_address_of_senders_account):
    next_nonce = w3.eth.get_transaction_count(public_address_of_senders_account)
    tx_nonces = [next_nonce + i for i in range(0, num_of_txs)] # account for approve tx

    t1_start = perf_counter()
    with concurrent.futures.ProcessPoolExecutor(8) as executor:
        result = list(executor.map(generate_cross_transfer_tx, tx_nonces))
        result.sort(key=lambda x: x[0])
        for (nonce, signed_tx) in result:
            tx_bytes = bytes.fromhex(signed_tx.rawTransaction.hex()[2:])
            length_of_tx = len(tx_bytes)
            f.write(length_of_tx.to_bytes(2, byteorder='little'))
            f.write(tx_bytes)
    t1_stop = perf_counter()
    print("Elapsed time during the whole program in seconds:", t1_stop - t1_start)


if __name__ == "__main__":
    generate_txs()