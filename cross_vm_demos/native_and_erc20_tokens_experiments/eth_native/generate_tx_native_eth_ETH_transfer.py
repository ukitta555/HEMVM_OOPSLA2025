# import concurrent
# from time import perf_counter
# from typing import BinaryIO
# from eth_typing import Address
# from hexbytes import HexBytes
# from web3 import Web3
#
# from uniswap_experiments.utils import eth_sign_tx
# from utils import eth_sign_and_write_tx_to_file
#
# w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
#
# num_of_txs = 10 ** 5
#
# def generate_native_transfer_tx(nonce: int):
#     sender = "0x14Dcb427A216216791fB63973c5b13878de30916"
#     receiver = "0x9ab64580dbf2bda277f20c3816003d42561640be"
#     # unsent_txn = {
#     #     'from': sender,
#     #     # 'chainId': 1337, # change to 1337 if want to run conflux experiments
#     #     'to': Address(HexBytes(receiver)),
#     #     'value': 1 * 10**10,
#     #     'nonce': nonce,
#     #     'gas': 21001,
#     #     'gasPrice': 10 ** 9 + 1,
#     # }
#     unsent_txn = {
#         "from": sender,
#         'gas': 30000000,
#         'gasPrice': 1,
#         'value': 1 * 10 ** 10,
#         "nonce": nonce,
#     }
#     print(f"Generated ETH transfer tx with nonce {nonce}")
#     signed_tx = eth_sign_tx(w3, unsent_txn)
#     return nonce, signed_tx
#
#
# def generate_and_write_swap_txs_parallel(f, public_address_of_senders_account):
#     next_nonce = w3.eth.get_transaction_count(public_address_of_senders_account)
#     tx_nonces = [next_nonce + i for i in range(0, num_of_txs)]
#
#     t1_start = perf_counter()
#     with concurrent.futures.ProcessPoolExecutor(8) as executor:
#         result = list(executor.map(generate_native_transfer_tx, tx_nonces))
#         result.sort(key=lambda x: x[0])
#         for (nonce, signed_tx) in result:
#             print(signed_tx.rawTransaction.hex()[0:2])
#
#             tx_bytes = bytes.fromhex(signed_tx.rawTransaction.hex()[2:])
#             length_of_tx = len(tx_bytes)
#             f.write(length_of_tx.to_bytes(2, byteorder='little'))
#             f.write(tx_bytes)
#     t1_stop = perf_counter()
#     print("Elapsed time during the whole program in seconds:", t1_stop - t1_start)
#
# def generate_txs():
#     sender = "0x14Dcb427A216216791fB63973c5b13878de30916"
#     with open("eth_native_token_intra_100k.txt", "wb") as f:
#         generate_and_write_swap_txs_parallel(f, sender)
#
# if __name__ == "__main__":
#     generate_txs()


# TODO: uncomment parallel tx generation above and try it again; seems like I wrote to a wrong file after all..
from typing import BinaryIO
from eth_typing import Address
from hexbytes import HexBytes
from web3 import Web3
from utils import eth_sign_and_write_tx_to_file

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

num_of_txs = 10 ** 5

def write_native_transfer_tx(
        file: BinaryIO,
        sender: str,
        receiver: str,
        current_txs: int
):
    unsent_txn = {
        'from': sender,
        # 'chainId': 1337,
        'chainId': 129,
        'to': Address(HexBytes(receiver)),
        'value': 1 * 10**10,
        'nonce': current_txs,
        'gas': 21001,
        'gasPrice': 10 ** 9 + 1,
    }

    print(f"Generated ETH transfer tx with nonce {current_txs}")
    eth_sign_and_write_tx_to_file(w3, file, unsent_txn)


def generate_txs():
    sender = "0x14Dcb427A216216791fB63973c5b13878de30916"
    receiver = "0x9ab64580dbf2bda277f20c3816003d42561640be"
    current_txs = w3.eth.get_transaction_count(sender)

    with open("eth_native_token_intra_100k.txt", "wb") as f:
        for i in range(0, num_of_txs):
            write_native_transfer_tx(
                file=f,
                sender=sender,
                receiver=receiver,
                current_txs=current_txs
            )
            current_txs += 1


if __name__ == "__main__":
    generate_txs()