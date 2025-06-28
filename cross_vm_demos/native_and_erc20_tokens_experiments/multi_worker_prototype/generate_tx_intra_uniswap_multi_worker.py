import asyncio
import random
from time import perf_counter

import concurrent
from eth_typing import Address
from hexbytes import HexBytes
from web3 import Web3


from funding_utils_local import approve_eth_custom_coin, fund_npc_accounts_custom_coin_aptos, fund_npc_accounts_custom_coin_eth, fund_npc_accounts_native_coin_aptos, fund_npc_accounts_native_coin_eth, register_lp_tokens_uniswap_cross_experiment, transfer_move_custom_coin_cross_space

from utils import TxType, cache_of_eth_addresses, eth_sign_tx_dynamic_pk, read_eth_keys, write_tx_to_file_with_tx_type
from local_abis import old_router_abi

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

K = 1000
num_of_txs = 500 * K


def sign_swap_tx(tx_and_pk: tuple[dict, str]):
    unsent_txn, sender_pk = tx_and_pk
    # print(f"Generated ETH transfer tx with nonce {unsent_txn['nonce']} for address {decode_eth_private_key_to_address(sender_pk)}")
    signed_tx = eth_sign_tx_dynamic_pk(w3, unsent_txn, sender_pk=sender_pk)
    return unsent_txn["nonce"], signed_tx

async def main():
    await fund_npc_accounts_native_coin_eth(
        eth_keys_path="../../experiment_runner/keys/private_keys_ethereum.txt"
    )
    await fund_npc_accounts_native_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt"
    )
    await fund_npc_accounts_custom_coin_eth(
        eth_keys_path="../../experiment_runner/keys/private_keys_ethereum.txt",
        only_eth_coin_deployed=False,
        erc_20_cross_setup=True
    )
    await fund_npc_accounts_custom_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt",
        erc_20_cross_setup=True
    )
    await approve_eth_custom_coin(
        eth_keys_path="../../experiment_runner/keys/private_keys_ethereum.txt",
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt"                
    )
    await transfer_move_custom_coin_cross_space(
        eth_keys_path="../../experiment_runner/keys/private_keys_ethereum.txt",
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt"
    )
    await register_lp_tokens_uniswap_cross_experiment(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt"
    )



    eth_private_keys = read_eth_keys()
    eth_nonces = dict()
    addresses = cache_of_eth_addresses(eth_private_keys=eth_private_keys)
    t1_start = perf_counter()
    unsigned_txs = []

    
    SwapETH = w3.eth.contract(address="0xa9B54DA9D0D2DbfB29d512d6babaA7D0f87E6959", abi=old_router_abi)
    coin_1 = Address(HexBytes("0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc"))
    coin_2 = Address(HexBytes("0x5ca0f43868e106ac9aec48f8f1285896c0b9865d"))
    

    for idx in range(num_of_txs):
        sender_pk = random.choice(eth_private_keys)

        sender_eth = addresses[sender_pk]

        if eth_nonces.get(sender_eth) is None:
            eth_nonces[sender_eth] = w3.eth.get_transaction_count(sender_eth)
        
        unsent_txn = SwapETH.functions.swapExactTokensForTokens(
            1000 * 10 ** 10,
            1,
            [coin_1, coin_2],
            sender_eth,
            1000000000000000000000000
        ).build_transaction({
            "from": sender_eth,
            'value': 0,
            'gas': 30000000,
            'gasPrice': 1,
            "nonce": eth_nonces[sender_eth],
        })

        # signed_tx = eth_sign_tx_dynamic_pk(w3, unsent_txn, sender_pk=sender_pk)
        # receipt = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        # w3.eth.wait_for_transaction_receipt(receipt)
        # print(w3.eth.get_transaction_receipt(receipt))

        eth_nonces[sender_eth] += 1
        unsigned_txs.append((unsent_txn, sender_pk))
        if idx % 1000 == 0:
            print(f"Txs generation progress: {idx * 100 / num_of_txs}%")
    t1_stop = perf_counter()


    t2_start = perf_counter()
    with concurrent.futures.ProcessPoolExecutor(12) as executor:
        # weird Python shenanigans - PPE deadlocks on large arrays, most likely problems with clogged pipes between processes
        result_1: list[int, dict] = list(executor.map(sign_swap_tx, unsigned_txs[0:100000]))
        result_2: list[int, dict] = list(executor.map(sign_swap_tx, unsigned_txs[100000:200000]))
        result_3: list[int, dict] = list(executor.map(sign_swap_tx, unsigned_txs[200000:300000]))
        result_4: list[int, dict] = list(executor.map(sign_swap_tx, unsigned_txs[300000:400000]))
        result_5: list[int, dict] = list(executor.map(sign_swap_tx, unsigned_txs[400000:500000]))
        result = result_1 + result_2 + result_3 + result_4 + result_5
        result.sort(key=lambda x: x[0])
        with open(f"./transaction_batches/uniswap_intra_multiworker_{num_of_txs // K}k.txt", "wb") as f:    
            for (_, signed_tx) in result:
                write_tx_to_file_with_tx_type(file=f, unsent_signed_txn=signed_tx, tx_type=TxType.NATIVE_ETH_TX)
    t2_stop = perf_counter()
    print("Elapsed time during the unsigned transaction generation in seconds:", t1_stop - t1_start)
    print("Elapsed time during the signing and sorting phase in seconds:", t2_stop - t2_start)
    print("Elapsed time in total", t2_stop - t1_start)    


if __name__ == "__main__":
    asyncio.run(main())