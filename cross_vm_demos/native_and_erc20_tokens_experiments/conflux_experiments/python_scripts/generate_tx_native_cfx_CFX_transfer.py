from typing import BinaryIO

from cfx_account import LocalAccount
from utils_cfx import cfx_sign_and_write_tx_to_file
from conflux_web3 import Web3

w3 = Web3(Web3.HTTPProvider("http://localhost:12539"))

num_of_txs = 10 ** 5

def write_native_transfer_tx(
        file: BinaryIO,
        sender: LocalAccount,
        receiver: LocalAccount,
        next_nonce: int
):
    unsent_txn = {
        'from': sender.address,
        'chainId': 1,
        'to': receiver.address,
        'value': 1 * 10**10,
        'nonce': next_nonce,
        'gas': 21001,
        'gasPrice': 1,
        'epochHeight': 100000,
        'storageLimit': 1000000

    }

    cfx_sign_and_write_tx_to_file(sender, file, unsent_txn)
    print(f"Generated CFX transfer tx with nonce {next_nonce}")

def generate_txs():
    sender: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa")
    receiver: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafb")

    next_nonce = w3.cfx.get_next_nonce(sender.address)

    with open("./transaction_files/native_cfx_transactions_100k.txt", "wb") as f:
        for i in range(0, num_of_txs):
            write_native_transfer_tx(
                file=f,
                sender=sender,
                receiver=receiver,
                next_nonce=next_nonce
            )
            next_nonce += 1


if __name__ == "__main__":
    generate_txs()