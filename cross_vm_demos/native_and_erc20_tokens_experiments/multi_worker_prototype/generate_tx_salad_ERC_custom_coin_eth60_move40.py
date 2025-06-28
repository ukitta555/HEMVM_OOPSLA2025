import asyncio
from path_setup import setup_cross_vm_demos_path
setup_cross_vm_demos_path()

from funding_utils_local import fund_npc_accounts_custom_coin_aptos, fund_npc_accounts_custom_coin_eth, fund_npc_accounts_native_coin_aptos, fund_npc_accounts_native_coin_eth


import random
import concurrent
from time import perf_counter
from aptos_sdk.account import Account
from eth_typing import Address
from hexbytes import HexBytes
from web3 import Web3
from utils import LIDLAptosSDK, TxType, cache_of_eth_addresses, cache_of_move_accounts, eth_sign_tx_dynamic_pk, eth_sign_tx_genesis, read_eth_keys, read_move_keys, write_tx_to_file_with_tx_type
from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument
from aptos_sdk.bcs import Serializer
from local_abis import eth_coin_abi


w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

K = 1000
num_of_txs = 500 * K


def generate_transfer_txs_move(move_private_keys, move_accounts, move_txs_counter):
    account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"

    move_txs = []
    sdk = LIDLAptosSDK()
    for idx in range(move_txs_counter):
        sender_pk = random.choice(move_private_keys)
        receiver_pk = sender_pk
        while receiver_pk == sender_pk:
            receiver_pk = random.choice(move_private_keys)

        sender_account = move_accounts[sender_pk]
        receiver_account = move_accounts[receiver_pk]

        transaction_arguments = [
            TransactionArgument(receiver_account.address(), Serializer.struct),
            TransactionArgument(10**4, Serializer.u64),
        ]

        payload = EntryFunction.natural(
            f"{account_address}::native_coin",
            "transfer",
            [],
            transaction_arguments,
        )

        move_txs.append(sdk.create_bcs_signed_transaction(sender_account, TransactionPayload(payload))) 
        if idx % 1000 == 0:
            print(f"Txs generation progress (Move): {idx * 100 / move_txs_counter}%") # TODO: fix progress bar

    return move_txs


def sign_erc20_transfer_tx(tx_and_pk: tuple):
    unsigned_tx, sender_pk = tx_and_pk
    signed_tx = eth_sign_tx_dynamic_pk(w3, unsigned_tx, sender_pk=sender_pk)
    print(f"Signed ERC20 transfer tx with nonce {unsigned_tx['nonce']}")
    return unsigned_tx["nonce"], signed_tx

def generate_transfer_txs_parallel_eth(eth_private_keys, addresses, eth_tx_count):
    ERC20Contract = w3.eth.contract(
        address="0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc",
        abi=eth_coin_abi
    )
    
    eth_nonces = dict()
    unsigned_txs = []
    for idx in range(eth_tx_count):
        sender_pk = random.choice(eth_private_keys)
        receiver_pk = sender_pk
        while receiver_pk == sender_pk:
            receiver_pk = random.choice(eth_private_keys)
        
        sender_eth = addresses[sender_pk]
        receiver_eth = addresses[receiver_pk]

        if eth_nonces.get(sender_eth) is None:
            eth_nonces[sender_eth] = 0 # to speed up the generation and not query the tx count for each of the wallets

        unsent_txn = ERC20Contract.functions.transfer(
            receiver_eth,
            10**10
        ).build_transaction(
            {
                "from": sender_eth,
                'value': 0,
                'chainId': 129,
                "gas": 3000000,
                "gasPrice": 10 ** 9 + 1,
                "nonce": eth_nonces[sender_eth],
            }
        )

        eth_nonces[sender_eth] += 1
        unsigned_txs.append((unsent_txn, sender_pk))
        if idx % 1000 == 0:
            print(f"Txs generation progress (Eth): {idx * 100 / eth_tx_count}%")

    t1_start = perf_counter()
    
    with concurrent.futures.ProcessPoolExecutor(12) as executor:
        # weird Python shenanigans - PPE deadlocks on large arrays, most likely problems with clogged pipes between processes
        result_1: list[int, dict] = list(executor.map(sign_erc20_transfer_tx, unsigned_txs[0:100000]))
        result_2: list[int, dict] = list(executor.map(sign_erc20_transfer_tx, unsigned_txs[100000:200000]))
        result_3: list[int, dict] = list(executor.map(sign_erc20_transfer_tx, unsigned_txs[200000:300000]))
        result_4: list[int, dict] = list(executor.map(sign_erc20_transfer_tx, unsigned_txs[300000:400000]))
        result_5: list[int, dict] = list(executor.map(sign_erc20_transfer_tx, unsigned_txs[400000:500000]))
        signed_eth_txs = result_1 + result_2 + result_3 + result_4 + result_5
        signed_eth_txs.sort(key=lambda x:x[0])
    
    eth_txs = list(map(lambda x: x[1], signed_eth_txs))
    t1_stop = perf_counter()

    print("Elapsed time during Eth tx generation in seconds:", t1_stop - t1_start)
    return eth_txs

async def generate_txs():
    await fund_npc_accounts_native_coin_eth(
        eth_keys_path="../../experiment_runner/keys/private_keys_ethereum.txt"
    )

    await fund_npc_accounts_native_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt",
    )

    await fund_npc_accounts_custom_coin_eth( 
        eth_keys_path="../../experiment_runner/keys/private_keys_ethereum.txt",
        only_eth_coin_deployed=False,
        erc_20_cross_setup=False
    )

    await fund_npc_accounts_custom_coin_aptos(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt",
        erc_20_cross_setup=False
    )

    genesis = "0x14Dcb427A216216791fB63973c5b13878de30916"
    eth_private_keys = read_eth_keys()
    move_private_keys = read_move_keys()
    eth_addresses = cache_of_eth_addresses(eth_private_keys=eth_private_keys)
    move_accounts = cache_of_move_accounts(move_private_keys=move_private_keys)


    def move_intra_case(coin: float):
        return 0 <= coin < 0.40

    def eth_intra_case(coin: float):
        return 0.40 <= coin < 1
    
    eth_intra_txs_counter = 0
    move_intra_txs_counter = 0

    for _ in range(num_of_txs):
        salad_random_coin = random.uniform(0, 1)
        if move_intra_case(salad_random_coin):
            move_intra_txs_counter += 1
        elif eth_intra_case(salad_random_coin):
            eth_intra_txs_counter += 1
        


    print(eth_intra_txs_counter)
    print(move_intra_txs_counter)

    eth_txs = generate_transfer_txs_parallel_eth(
        eth_private_keys=eth_private_keys,
        addresses=eth_addresses,
        eth_tx_count=eth_intra_txs_counter
    )
    move_txs = generate_transfer_txs_move(
        move_private_keys=move_private_keys,
        move_accounts=move_accounts,     
        move_txs_counter=move_intra_txs_counter
    )

    
    eth_tx_idx = 0
    move_tx_idx = 0
    

    with open(f"./transaction_batches/salad_ERC_custom_coin_e60_m40_{num_of_txs // K}k.txt", "wb") as f:
        for _ in range(num_of_txs):
            if eth_tx_idx >= len(eth_txs):
                write_tx_to_file_with_tx_type(file=f, unsent_signed_txn=move_txs[move_tx_idx], tx_type=TxType.NATIVE_APTOS_TX)
                move_tx_idx += 1
            elif move_tx_idx >= len(move_txs):
                write_tx_to_file_with_tx_type(file=f, unsent_signed_txn=eth_txs[eth_tx_idx], tx_type=TxType.NATIVE_ETH_TX) 
                eth_tx_idx += 1
            else: 
                position_random_coin = random.uniform(0, 1)
                if position_random_coin < 0.4:
                    write_tx_to_file_with_tx_type(file=f, unsent_signed_txn=move_txs[move_tx_idx], tx_type=TxType.NATIVE_APTOS_TX)
                    move_tx_idx += 1
                else:
                    write_tx_to_file_with_tx_type(file=f, unsent_signed_txn=eth_txs[eth_tx_idx], tx_type=TxType.NATIVE_ETH_TX) 
                    eth_tx_idx += 1

if __name__ == "__main__":
    t1_start = perf_counter()
    asyncio.run(generate_txs())
    t1_stop = perf_counter()
    print("Elapsed time during the whole program in seconds:", t1_stop - t1_start)