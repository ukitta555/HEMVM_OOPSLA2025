import concurrent
from time import perf_counter
from typing import BinaryIO

from cfx_account import LocalAccount
from conflux_web3.contract import ConfluxContract


from abis import core_coin_abi
from utils_cfx import cfx_sign_and_write_tx_to_file
from conflux_web3 import Web3

w3 = Web3(Web3.HTTPProvider("http://localhost:12539"))

num_of_txs = 10 ** 5

def write_ERC20_transfer_tx(
        file: BinaryIO,
        sender: LocalAccount,
        receiver: LocalAccount,
        next_nonce: int
):
    CoreSpaceCoin: ConfluxContract = w3.cfx.contract(address="CFXTEST:TYPE.CONTRACT:ACHB9SHENUM2XP1BSJ2XDRB4F7VEKNSMUUSHBVCNSF", abi=core_coin_abi)

    # 0x6fd3211ebbfa9e85edeef993cf5d8f7f8ed818a3edf1ee152c11a485b92d87b0 first hash
    # 0xdaf37d94170eff61c2b530c8067e56fad435a7c5e3348189adaf5d8516aab34a last hash
    unsent_txn = CoreSpaceCoin.functions.transfer(
        receiver.address,
        10 ** 13
    ).build_transaction(
        {
            "from": sender.address,
            'value': 0,
            'gas': 3000000,
            'gasPrice': 1,
            "nonce": next_nonce,
            'epochHeight': 100000,
            'storageLimit': 1000000
        }
    )

    cfx_sign_and_write_tx_to_file(sender, file, unsent_txn)
    print(f"Generated ERC-20 transfer tx with nonce {next_nonce}")



def generate_txs():
    sender: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa")
    receiver: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafb")

    next_nonce = w3.cfx.get_next_nonce(sender.address)

    with open("./transaction_files/erc20_transactions.txt", "wb") as f:
        t1_start = perf_counter()
        for i in range(0, num_of_txs):
            write_ERC20_transfer_tx(
                file=f,
                sender=sender,
                receiver=receiver,
                next_nonce=next_nonce
            )
            next_nonce += 1
        t1_stop = perf_counter()

        print("Elapsed time during the whole program in seconds:", t1_stop-t1_start)

def write_ERC20_transfer_tx_parallel(
    nonce: int
):

    sender: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa")
    receiver: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafb")

    CoreSpaceCoin: ConfluxContract = w3.cfx.contract(address="CFXTEST:TYPE.CONTRACT:ACHB9SHENUM2XP1BSJ2XDRB4F7VEKNSMUUSHBVCNSF", abi=core_coin_abi)
    unsent_txn = CoreSpaceCoin.functions.transfer(
        receiver.address,
        10 ** 13
    ).build_transaction(
        {
            "from": sender.address,
            'value': 0,
            'gas': 3000000,
            'gasPrice': 1,
            "nonce": nonce,
            'epochHeight': 100000,
            'storageLimit': 1000000
        }
    )

    signed_tx = sender.sign_transaction(unsent_txn)
    print(f"Generated ERC-20 transfer tx with nonce {nonce}")
    return nonce, signed_tx

def generate_txs_parallel():

    sender: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa")
    receiver: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafb")

    next_nonce = w3.cfx.get_next_nonce(sender.address)

    tx_nonces = [next_nonce + i for i in range(0, 100000)]

    with open("erc20_transactions_parallel.txt", "wb") as f:
        t1_start = perf_counter()
        with concurrent.futures.ProcessPoolExecutor(8) as executor:
            result = list(executor.map(write_ERC20_transfer_tx_parallel, tx_nonces))
            result.sort(key=lambda x: x[0])
            for (nonce, signed_tx) in result:
                tx_bytes = bytes.fromhex(signed_tx.rawTransaction.hex()[2:])
                length_of_tx = len(tx_bytes)
                f.write(length_of_tx.to_bytes(2, byteorder='little'))
                f.write(tx_bytes)
        t1_stop = perf_counter()
        print("Elapsed time during the whole program in seconds:", t1_stop-t1_start)


if __name__ == "__main__":
    generate_txs()
    # generate_txs_parallel()