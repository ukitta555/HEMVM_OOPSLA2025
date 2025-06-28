import concurrent
from time import perf_counter

from cfx_account import LocalAccount
from conflux_web3 import Web3

w3 = Web3(Web3.HTTPProvider("http://localhost:12539"))

num_of_txs = 10 ** 5

def write_cross_space_CFX_transfer_tx_parallel(
        nonce: int
):

    sender: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa")
    receiver: str = "0x471934422642acf5f667370d74bd0732e3911d32"

    CrossSpaceCall = w3.cfx.contract(name="CrossSpaceCall")
    unsent_txn = CrossSpaceCall.functions.transferEVM(
        receiver
    ).build_transaction(
        {
            "from": sender.address,
            'value': 10 ** 13,
            'gas': 3000000,
            'gasPrice': 1,
            "nonce": nonce,
            'epochHeight': 100000,
            'storageLimit': 1000000
        }
    )

    signed_tx = sender.sign_transaction(unsent_txn)
    print(f"Hash of tx with nonce {nonce}: {signed_tx.hash.hex()}")
    print(f"Generated cross-space CFX transfer tx with nonce {nonce}")
    return nonce, signed_tx

def generate_txs_parallel():

    sender: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa")
    receiver: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafb")

    next_nonce = w3.cfx.get_next_nonce(sender.address)
    print(next_nonce)
    tx_nonces = [next_nonce + i for i in range(0, 100000)]

    with open("./transaction_files/cross_native_CFX_transfer_transactions_parallel.txt", "wb") as f:
        t1_start = perf_counter()
        with concurrent.futures.ProcessPoolExecutor(8) as executor:
            result = list(executor.map(write_cross_space_CFX_transfer_tx_parallel, tx_nonces))
            result.sort(key=lambda x: x[0])
            for (nonce, signed_tx) in result:
                tx_bytes = bytes.fromhex(signed_tx.rawTransaction.hex()[2:])
                length_of_tx = len(tx_bytes)
                f.write(length_of_tx.to_bytes(2, byteorder='little'))
                f.write(tx_bytes)
        t1_stop = perf_counter()
        print("Elapsed time during the whole program in seconds:", t1_stop-t1_start)


if __name__ == "__main__":
    generate_txs_parallel()