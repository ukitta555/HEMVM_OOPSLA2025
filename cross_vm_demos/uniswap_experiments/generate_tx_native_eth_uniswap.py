import concurrent
from time import perf_counter

from eth_typing import Address
from hexbytes import HexBytes
from web3 import Web3

from abis import old_coin_abi, old_router_abi
from utils import eth_sign_and_write_tx_to_file, eth_sign_tx

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

num_of_txs = 10 ** 5

def write_approve_transactions(ETHCoin, ETHSwapRouter, f, public_address_of_senders_account):
    current_txs = w3.eth.get_transaction_count(public_address_of_senders_account)
    unsent_txn = ETHCoin.functions.approve(ETHSwapRouter.address, 2 ** 255) \
        .build_transaction(
        {
            "from": public_address_of_senders_account,
            'value': 0,
            'gas': 30000000,
            'gasPrice': 1,
            "nonce": current_txs,
        }
    )
    print("Nonce: ", current_txs)
    eth_sign_and_write_tx_to_file(w3, f, unsent_txn)


# def write_swap_txs(SwapETH, current_txs, coin_1, coin_2, f, public_address_of_senders_account):
#     for transaction_id in range(1, num_of_txs + 1):
#         # if transaction_id % 1000 == 0:
#         #    print(f"Generated {transaction_id} tx")
#         raw_txn = SwapETH.functions.swapExactTokensForTokens(
#             1000 * 10 ** 10,
#             1,
#             [coin_1, coin_2],
#             public_address_of_senders_account,
#             1000000000000000000000000
#         ).build_transaction({
#             "from": public_address_of_senders_account,
#             'value': 0,
#             'gas': 30000000,
#             'gasPrice': 1,
#             "nonce": current_txs + transaction_id,  # + 1 for the approve tx
#         })
#         print("Nonce: ", current_txs + transaction_id)
#         eth_sign_and_write_tx_to_file(w3, f, raw_txn)


def generate_transactions():
    SwapETH = w3.eth.contract(address="0x866A4a061De0f196205dfF79B3c47700b570f617", abi=old_router_abi)
    public_address_of_senders_account = "0x14Dcb427A216216791fB63973c5b13878de30916"

    with open("uniswap_intra_100k.txt", "wb") as f:
        ETHCoin = w3.eth.contract(address="0x866A4a061De0f196205dfF79B3c47700b570f617", abi=old_coin_abi)
        # write_approve_transactions(ETHCoin, SwapETH, f, public_address_of_senders_account)
        # write_swap_txs(SwapETH, current_txs, coin_2, coin_1, f, public_address_of_senders_account)
        generate_and_write_swap_txs_parallel(f, public_address_of_senders_account)


def generate_and_write_swap_txs_parallel(f, public_address_of_senders_account):
    next_nonce = w3.eth.get_transaction_count(public_address_of_senders_account)
    tx_nonces = [next_nonce + i for i in range(0, num_of_txs)]

    t1_start = perf_counter()
    with concurrent.futures.ProcessPoolExecutor(8) as executor:
        result = list(executor.map(write_native_swap_tx_parallel, tx_nonces))
        result.sort(key=lambda x: x[0])
        for (nonce, signed_tx) in result:
            tx_bytes = bytes.fromhex(signed_tx.rawTransaction.hex()[2:])
            length_of_tx = len(tx_bytes)
            f.write(length_of_tx.to_bytes(2, byteorder='little'))
            f.write(tx_bytes)
    t1_stop = perf_counter()
    print("Elapsed time during the whole program in seconds:", t1_stop - t1_start)

def write_native_swap_tx_parallel(nonce: int):
    SwapETH = w3.eth.contract(address="0x866A4a061De0f196205dfF79B3c47700b570f617", abi=old_router_abi)
    public_address_of_senders_account = "0x14Dcb427A216216791fB63973c5b13878de30916"
    coin_1 = Address(HexBytes("0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc"))
    coin_2 = Address(HexBytes("0x812cBBdE09AF8214a5c3addE18Fcec9891196494"))

    raw_txn = SwapETH.functions.swapExactTokensForTokens(
        1000 * 10 ** 10,
        1,
        [coin_1, coin_2],
        public_address_of_senders_account,
        1000000000000000000000000
    ).build_transaction({
        "from": public_address_of_senders_account,
        'value': 0,
        'gas': 30000000,
        'gasPrice': 1,
        "nonce": nonce,
    })
    print("Nonce inside parallel loop: ", nonce)
    signed_tx = eth_sign_tx(w3, raw_txn)
    return nonce, signed_tx


def main():
    print("Starting to generate txs....")
    generate_transactions()
    print("Generated all required txs.")

if __name__ == '__main__':
    main()

