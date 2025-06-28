import asyncio
import time


from funding_utils_local import approve_eth_custom_coin, approve_eth_custom_coin_pancakeswap_cross, fund_npc_accounts_custom_coin_aptos, fund_npc_accounts_custom_coin_eth, fund_npc_accounts_native_coin_aptos, fund_npc_accounts_native_coin_eth, register_custom_coin_pancakeswap_native

from aptos_sdk.type_tag import TypeTag, StructTag
import random
import concurrent
from time import perf_counter
from web3 import Web3
from utils import LIDLAptosSDK, TxType, cache_of_eth_addresses, cache_of_move_accounts, decode_eth_private_key_to_address, eth_sign_tx_dynamic_pk, eth_sign_tx_genesis, read_eth_keys, read_move_keys, write_tx_to_file_with_tx_type
from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument
from aptos_sdk.bcs import Serializer
from local_abis import eth_coin_abi, vault_abi, old_router_abi, move_router_abi


w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

K = 1000
num_of_txs = 500 * K


def generate_transfer_txs_move(
    move_private_keys,
    eth_private_keys, 
    move_accounts, 
    eth_addresses,
    move_txs_counter
):
    deployer_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
    router_address = "0x7a526ec5f06a7976caec96614f0db691f53b452424a3897a18a115ddd300c110"

    move_txs = []
    move_tx_types = []
    sdk = LIDLAptosSDK()
    for idx in range(move_txs_counter):
        sender_pk = random.choice(move_private_keys)
        sender_account = move_accounts[sender_pk]
        
        receiver_pk = sender_pk
        while receiver_pk == sender_pk:
            receiver_pk = random.choice(move_private_keys)
        receiver_account = move_accounts[receiver_pk]

        payload = EntryFunction.natural(
            f"{router_address}::router",
            "swap_exact_input",
            [
                TypeTag(StructTag.from_str(f"{deployer_address}::native_coin::DiemCoin")),
                TypeTag(StructTag.from_str(f"{deployer_address}::native_coin_2::DiemCoin2"))
            ],
            [
                TransactionArgument(10 ** 5, Serializer.u64),
                TransactionArgument(1, Serializer.u64),
            ],
        )
        move_tx_types.append(TxType.NATIVE_APTOS_TX)
        
        move_txs.append(sdk.create_bcs_signed_transaction(sender_account, TransactionPayload(payload))) 
        if idx % 1000 == 0:
            print(f"Txs generation progress (Move): {idx * 100 / move_txs_counter}%") 

    return move_txs, move_tx_types


def sign_erc20_transfer_tx(tx_and_pk_and_tx_type: tuple):
    unsigned_tx, sender_pk, tx_type = tx_and_pk_and_tx_type
    signed_tx = eth_sign_tx_dynamic_pk(w3, unsigned_tx, sender_pk=sender_pk)
    print(f"Signed txn with nonce {unsigned_tx['nonce']}")
    return unsigned_tx["nonce"], signed_tx, tx_type


# need to merge the generation of intra and cross transactions
# need to flip a coin here instead of a parent method?
# depending on the coin flip, generate either a intra or a cross transaction
# signing does not change depending on the case we are in - can simply send to a parallelized executor 
def generate_transfer_txs_parallel_eth(
    eth_private_keys,
    move_private_keys,  
    eth_addresses,
    move_accounts, 
    eth_tx_count
):
    ERC20Contract = w3.eth.contract(
        address="0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc",
        abi=eth_coin_abi
    )
    
    eth_nonces = dict()
    unsigned_txs = []


    MoveSwapRouter = w3.eth.contract(address="0x13157441585494b5E09E066e69C779aEa08d164B", abi=move_router_abi)
    SwapETH = w3.eth.contract(address="0xa9B54DA9D0D2DbfB29d512d6babaA7D0f87E6959", abi=old_router_abi)
    coin_1 = "0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc" 
    coin_2 = Web3.to_checksum_address("0x5ca0f43868e106ac9aec48f8f1285896c0b9865d")

    
    for idx in range(eth_tx_count):
        sender_pk = random.choice(eth_private_keys)        
        sender_eth = eth_addresses[sender_pk]      

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
            "chainId": 129,
            'gas': 30000000,
            'gasPrice': 1,
            "nonce": eth_nonces[sender_eth],
        })
        tx_type = TxType.NATIVE_ETH_TX
         
        eth_nonces[sender_eth] += 1
        unsigned_txs.append((unsent_txn, sender_pk, tx_type))
        if idx % 1000 == 0:
            print(f"Txs generation progress (Eth): {idx * 100 / eth_tx_count}%")

    t1_start = perf_counter()
    
    # TODO: loop with intervals of 100k txs; remove hardcoded intervals, in this case there might be less than 500k eth transactions!
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
    eth_tx_types = list(map(lambda x: x[2], signed_eth_txs))
    print(len(eth_txs), len(eth_tx_types))    
    
    t1_stop = perf_counter()

    print("Elapsed time during Eth tx generation in seconds:", t1_stop - t1_start)
    return eth_txs, eth_tx_types

async def generate_txs():
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
    await register_custom_coin_pancakeswap_native(
        aptos_keys_path="../../experiment_runner/keys/private_keys_aptos.txt",
    )
    
    eth_private_keys = read_eth_keys()
    move_private_keys = read_move_keys()
    eth_addresses = cache_of_eth_addresses(eth_private_keys=eth_private_keys)
    move_accounts = cache_of_move_accounts(move_private_keys=move_private_keys)

    # these cases will be split later in the child method depending on the value of the another coin 
    # coin cases in the child method will depend on the probabilities we need 
    def move_case(coin: float):
        return 0 <= coin < 0.5

    def eth_case(coin: float):
        return 0.5 <= coin < 1 
    
    eth_txs_number = 0
    move_txs_number = 0

    for _ in range(num_of_txs):
        salad_random_coin = random.uniform(0, 1)
        if move_case(salad_random_coin):
            move_txs_number += 1
        elif eth_case(salad_random_coin):
            eth_txs_number += 1


    print(f"Number of ETH transactions: {eth_txs_number}")
    print(f"Number of Aptos transactions: {move_txs_number}")

    time.sleep(3)

    # need to correctly specify to the file_writer that certain transactions are cross space and others are intra-space
    # For Move case, relatively easy since we generate them sequentially - can attach an array of tags that represents the types of the transactions
    # For Ethereum case, we generate the transactions in parallel and then sort them
    # Save the tag when generating the transactions, pass it to the signing parallel execution, 
    # get it back with signed tx and write it to the types array
    eth_txs, eth_tx_types = generate_transfer_txs_parallel_eth(
        eth_private_keys=eth_private_keys,
        move_private_keys=move_private_keys,
        eth_addresses=eth_addresses,
        move_accounts=move_accounts,
        eth_tx_count=eth_txs_number,
    )
    assert len(eth_txs) == len(eth_tx_types) == eth_txs_number

    move_txs, move_tx_types = generate_transfer_txs_move(
        move_private_keys=move_private_keys,
        eth_private_keys=eth_private_keys,
        move_accounts=move_accounts,     
        eth_addresses=eth_addresses,
        move_txs_counter=move_txs_number,
    )
    assert len(move_txs) == len(move_tx_types) == move_txs_number

    
    eth_tx_idx = 0
    move_tx_idx = 0
    
    
    with open(f"./transaction_batches/salad_uniswap_pancake_uni45_pancake55_{num_of_txs // K}k.txt", "wb") as f:
        for _ in range(num_of_txs):
            if eth_tx_idx >= len(eth_txs):
                write_tx_to_file_with_tx_type(file=f, unsent_signed_txn=move_txs[move_tx_idx], tx_type=move_tx_types[move_tx_idx])
                move_tx_idx += 1
            elif move_tx_idx >= len(move_txs):
                write_tx_to_file_with_tx_type(file=f, unsent_signed_txn=eth_txs[eth_tx_idx], tx_type=eth_tx_types[eth_tx_idx]) 
                eth_tx_idx += 1
            else: 
                position_random_coin = random.uniform(0, 1)
                if move_case(position_random_coin):
                    write_tx_to_file_with_tx_type(file=f, unsent_signed_txn=move_txs[move_tx_idx], tx_type=move_tx_types[move_tx_idx])
                    move_tx_idx += 1
                elif eth_case(position_random_coin):
                    write_tx_to_file_with_tx_type(file=f, unsent_signed_txn=eth_txs[eth_tx_idx], tx_type=eth_tx_types[eth_tx_idx]) 
                    eth_tx_idx += 1

if __name__ == "__main__":
    t1_start = perf_counter()
    asyncio.run(generate_txs())
    t1_stop = perf_counter()
    print("Elapsed time during the whole program in seconds:", t1_stop - t1_start)