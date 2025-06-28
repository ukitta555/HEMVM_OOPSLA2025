import concurrent
from time import perf_counter

from eth_typing import Address
from hexbytes import HexBytes
from web3 import Web3

from abis import abi, eth_coin_abi
from utils import eth_sign_and_write_tx_to_file, eth_sign_tx

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

num_of_txs = 10 ** 5


def write_native_swap_tx_parallel(nonce: int):
    public_address_of_senders_account = "0x14Dcb427A216216791fB63973c5b13878de30916"
    SwapETH = w3.eth.contract(address="0x812cBBdE09AF8214a5c3addE18Fcec9891196494", abi=abi)
    eth_coin = Address(HexBytes("0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc"))
    emc_coin = Web3.to_checksum_address("0x5ca0f43868e106ac9aec48f8f1285896c0b9865d")
    ETHCoin = w3.eth.contract(address="0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc", abi=eth_coin_abi)

    raw_txn = SwapETH.functions.swapExactTokensForTokens(
        Address(eth_coin),
        emc_coin,
        1000 * 10 ** 10,
        1,
    ).build_transaction({
        "from": public_address_of_senders_account,
        'value': 0,
        'gas': 30000000,
        'gasPrice': 1,
        "nonce": nonce,  # + 1 for the approve tx
    })
    print("Nonce inside parallel loop: ", nonce)
    signed_tx = eth_sign_tx(w3, raw_txn)
    return nonce, signed_tx


def generate_and_write_swap_txs_parallel(f, public_address_of_senders_account):
    next_nonce = w3.eth.get_transaction_count(public_address_of_senders_account) + 2
    tx_nonces = [next_nonce + i for i in range(0, 100000)]

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


def write_approve_transactions(f):
    public_address_of_senders_account = "0x14Dcb427A216216791fB63973c5b13878de30916"
    ETHSwap = w3.eth.contract(address="0x812cBBdE09AF8214a5c3addE18Fcec9891196494", abi=abi)
    ETHCoin = w3.eth.contract(address="0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc", abi=eth_coin_abi)
    current_txs = w3.eth.get_transaction_count(public_address_of_senders_account)

    unsent_txn = ETHCoin.functions.approve("0x812cBBdE09AF8214a5c3addE18Fcec9891196494", 2 ** 255) \
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

    unsent_txn = ETHSwap.functions.approvePortal(ETHCoin.address) \
        .build_transaction(
        {
            "from": public_address_of_senders_account,
            'value': 0,
            'gas': 30000000,
            'gasPrice': 1,
            "nonce": current_txs + 1,
        }
    )
    print("Nonce: ", current_txs + 1)
    eth_sign_and_write_tx_to_file(w3, f, unsent_txn)
    print("Approved spending for the portal contract")


def generate_transactions():
    public_address_of_senders_account = "0x14Dcb427A216216791fB63973c5b13878de30916"
    with open("pancake_cross_100k.txt", "wb") as f:
        write_approve_transactions(f)
        generate_and_write_swap_txs_parallel(f, public_address_of_senders_account)


def main():
    print("Starting to generate txs....")
    generate_transactions()
    print("Generated all required txs.")


if __name__ == '__main__':
    main()

