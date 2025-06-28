import enum

import traceback


from web3 import Web3
from web3.eth import AsyncEth

import asyncio

from pprint import pprint
from eth_typing import Address
from hexbytes import HexBytes
from eth_account import Account as EthAccount
from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.async_client import RestClient, FaucetClient, ClientConfig
from aptos_sdk.transactions import EntryFunction, TransactionPayload, TransactionArgument
from aptos_sdk.type_tag import TypeTag, StructTag
from local_abis import eth_coin_abi, portal_abi

# TODO: this file needs MAJOR REFACTORING. 
# A large portion of bigger experiments were done in a deadline rush and might have redundant function calls.

def eth_sign_tx_genesis(w3: Web3, unsent_tx):
    return w3.eth.account.sign_transaction(
        unsent_tx,
        private_key="fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa",
    )

def eth_sign_tx_dynamic_pk(w3: Web3, unsent_tx, sender_pk: str):
    return w3.eth.account.sign_transaction(
        unsent_tx,
        private_key=sender_pk
    )

def decode_eth_private_key_to_address(private_key):
    return EthAccount.from_key(private_key).address

class FundingType(enum.Enum):
    NO_FUNDING = 0
    NATIVE_ETH = 1
    NATIVE_APTOS = 2
    NATIVE_BOTH = 3
    NATIVE_AND_CUSTOM_ETH = 4
    NATIVE_AND_CUSTOM_APTOS = 5
    NATIVE_AND_CUSTOM_BOTH = 6
    UNISWAP_EXPERIMENT = 7
    UNISWAP_CROSS_EXPERIMENT = 8
    PANCAKE_EXPERIMENT = 9
    PANCAKE_CROSS_EXPERIMENT = 10
    MIX_UNISWAP_EXPERIMENT = 11
    MIX_PANCAKE_EXPERIMENT_NATIVE_ONLY = 12
    MIX_PANCAKE_EXPERIMENT_NATIVE_AND_CROSS = 13
    MIX_UNI_PANCAKE_NATIVE_EXPERIMENT = 14
    MIX_UNI_PANCAKE_CROSS_EXPERIMENT = 15

w3 = Web3(Web3.AsyncHTTPProvider("http://127.0.0.1:8545"), modules={'eth': (AsyncEth,)}, middlewares=[])

# TODO: refactor using Path python objects (or use global paths) to avoid specifying custom paths when using these functions from different files
async def execute_batch_of_eth_txs(txs: list):
    hashes = await asyncio.gather(*list(map(w3.eth.send_raw_transaction, txs)))
    await asyncio.gather(*list(map(w3.eth.wait_for_transaction_receipt, hashes)))

async def execute_batch_of_aptos_txs(rest_client: RestClient, txs: list):
    print(f"{len(txs)} sent to be processed")
    step = 100
    for idx in range(0, len(txs), step):
        hashes = await asyncio.gather(*list(map(rest_client.submit_bcs_transaction, txs[idx:idx+step])))
        await asyncio.gather(*list(map(rest_client.wait_for_transaction, hashes)))
        if idx % 200 == 0:
            print(f"{idx} Aptos txs processed!")


async def register_custom_coin_pancakeswap_native(
    aptos_keys_path: str
):
    rest_client = RestClient("http://127.0.0.1:8080/v1")
    with open(aptos_keys_path) as file:
        lines = file.readlines()
        move_accounts = list(map(lambda key: Account.load_key(key.strip()), lines))
        move_addresses = list(map(lambda key: Account.load_key(key.strip()).address(), lines))
    
    deployer_account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
    payload = EntryFunction.natural(
        f"0x1::managed_coin",
        "register",
        [TypeTag(StructTag.from_str(f"{deployer_account_address}::native_coin_2::DiemCoin2"))],
        [],
    )

    txs = []
    for recipient in move_accounts:
        txs.append(await rest_client.create_bcs_signed_transaction(recipient, TransactionPayload(payload)))
    await execute_batch_of_aptos_txs(rest_client=rest_client, txs=txs)



async def approve_eth_custom_coin_pancakeswap_cross(
    eth_keys_path: str,
    double_dex: bool = False
):
    with open(eth_keys_path) as file:
        eth_keys = file.readlines()
        
    eth_addresses = list(map(lambda key: decode_eth_private_key_to_address(key.strip()), eth_keys))

    ERC20Contract = w3.eth.contract(
        address="0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc",
        abi=eth_coin_abi
    )
    
    move_router_address = "0x13157441585494b5E09E066e69C779aEa08d164B" if double_dex else "0x812cBBdE09AF8214a5c3addE18Fcec9891196494" 
    unsent_signed_txs = []
    for eth_key, eth_address in zip(eth_keys, eth_addresses):
        # approve the transfer of tokens    
        unsent_tx = await ERC20Contract.functions.approve(
            Web3.to_checksum_address(move_router_address), 
            2 ** 255
        ).build_transaction(
            {
                "from": eth_address,
                'value': 0,
                'gas': 3000000,
                'chainId': 129,
                'gasPrice': 10 ** 9 + 1,
                "nonce": await w3.eth.get_transaction_count(eth_address),   
            }
        )
        signed_tx = eth_sign_tx_dynamic_pk(w3, unsent_tx=unsent_tx, sender_pk=eth_key.strip())
        unsent_signed_txs.append(signed_tx.rawTransaction)

    await execute_batch_of_eth_txs(txs=unsent_signed_txs)
    print("Approved transfers to MoveRouter!")


async def approve_eth_custom_coin(
    eth_keys_path: str,
    aptos_keys_path: str
):
    print("Approving eth coin transfers..")
    with open(eth_keys_path) as file:
        eth_keys = file.readlines()
        
    eth_addresses = list(map(lambda key: decode_eth_private_key_to_address(key.strip()), eth_keys))
    
    with open(aptos_keys_path) as file:
        lines = file.readlines()
        move_accounts = list(map(lambda key: Account.load_key(key.strip()), lines))
        move_addresses = list(map(lambda key: Account.load_key(key.strip()).address(), lines))

    assert len(move_addresses) == len(eth_addresses)

    router_address = "0xa9B54DA9D0D2DbfB29d512d6babaA7D0f87E6959"
    portal_address = "0x7d3d6e9f5ab582112c5cdbd712e808b2a4eafa5d"
    ERC20Contract = w3.eth.contract(
            address="0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc",
            abi=eth_coin_abi
    )
    
    unsent_signed_txs = []
    for eth_key, eth_address in zip(eth_keys, eth_addresses):
        # approve the transfer of tokens    
        unsent_tx = await ERC20Contract.functions.approve(
            Web3.to_checksum_address(portal_address), 
            2 ** 255
        ).build_transaction(
            {
                "from": eth_address,
                'value': 0,
                'gas': 3000000,
                'chainId': 129,
                'gasPrice': 10 ** 9 + 1,
                "nonce": await w3.eth.get_transaction_count(eth_address),   
            }
        )
        signed_tx = eth_sign_tx_dynamic_pk(w3, unsent_tx=unsent_tx, sender_pk=eth_key.strip())
        unsent_signed_txs.append(signed_tx.rawTransaction)

    await execute_batch_of_eth_txs(txs=unsent_signed_txs)
    print("Approved transfers to vault") # might be redundant? needed for cross space transfers

    print("Approving transfers to router..") 
    unsent_signed_txs = []
    for eth_key, eth_address in zip(eth_keys, eth_addresses):
        # approve the transfer of tokens    
        unsent_tx = await ERC20Contract.functions.approve(
            Web3.to_checksum_address(router_address), 
            2 ** 255
        ).build_transaction(
            {
                "from": eth_address,
                'value': 0,
                'gas': 3000000,
                'chainId': 129,
                'gasPrice': 10 ** 9 + 1,
                "nonce": await w3.eth.get_transaction_count(eth_address),   
            }
        )
        signed_tx = eth_sign_tx_dynamic_pk(w3, unsent_tx=unsent_tx, sender_pk=eth_key.strip())
        unsent_signed_txs.append(signed_tx.rawTransaction)

    await execute_batch_of_eth_txs(txs=unsent_signed_txs)
    print("Approved transfers to router..") 


async def register_mirror_eth_coin(
    aptos_keys_path: str
):
    rest_client = RestClient("http://127.0.0.1:8080/v1")
    deployer_account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
    print("Registering mirror coin so that accounts can accept it..")


    with open(aptos_keys_path) as file:
        lines = file.readlines()
        move_accounts = list(map(lambda key: Account.load_key(key.strip()), lines))
        move_addresses = list(map(lambda key: Account.load_key(key.strip()).address(), lines))

    payload = EntryFunction.natural(
        f"0x1::managed_coin",
        "register",
        [TypeTag(StructTag.from_str(f"{deployer_account_address}::mirror_coin::EthCoin"))],
        [],
    )

    txs = []
    for recipient in move_accounts:
        txs.append(await rest_client.create_bcs_signed_transaction(recipient, TransactionPayload(payload)))
    await execute_batch_of_aptos_txs(rest_client=rest_client, txs=txs)






async def transfer_eth_custom_coin_cross_space(
    eth_keys_path: str,
    aptos_keys_path: str
):
    print("Transfering ETH custom coins cross space...")
    rest_client = RestClient("http://127.0.0.1:8080/v1")
    deployer_account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"

    with open(eth_keys_path) as file:
        eth_keys = file.readlines()
        
    eth_addresses = list(map(lambda key: decode_eth_private_key_to_address(key.strip()), eth_keys))
    
    with open(aptos_keys_path) as file:
        lines = file.readlines()
        move_accounts = list(map(lambda key: Account.load_key(key.strip()), lines))
        move_addresses = list(map(lambda key: Account.load_key(key.strip()).address(), lines))

    portal_address = "0x7d3d6e9f5ab582112c5cdbd712e808b2a4eafa5d"
    ERC20Contract = w3.eth.contract(
            address="0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc",
            abi=eth_coin_abi
    )

    await register_mirror_eth_coin(aptos_keys_path=aptos_keys_path)

    PortalETH = w3.eth.contract(
        address=portal_address,
        abi=portal_abi
    )
    
    unsent_signed_txs = []
    idx = 0
    for eth_key, eth_address in zip(eth_keys, eth_addresses):
        # transfer tokens cross-space; assuming len(move_addresses) == len(eth_addresses)
        move_recipient = move_addresses[idx]   
        unsent_tx = await PortalETH.functions.deposit(
            move_recipient, 
            10 ** 9
        ).build_transaction(
            {
                "from": eth_address,
                'value': 0,
                'gas': 3000000,
                'chainId': 129,
                'gasPrice': 10 ** 9 + 1,
                "nonce": await w3.eth.get_transaction_count(eth_address),   
            }
        )
        signed_tx = eth_sign_tx_dynamic_pk(w3, unsent_tx=unsent_tx, sender_pk=eth_key.strip())
        unsent_signed_txs.append(signed_tx.rawTransaction)
        idx += 1

    await execute_batch_of_eth_txs(txs=unsent_signed_txs)


async def transfer_move_custom_coin_cross_space(
    eth_keys_path: str,
    aptos_keys_path: str
):
    print("Transfering Move custom coins cross space...")
    rest_client = RestClient("http://127.0.0.1:8080/v1")
    deployer_account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
    with open(eth_keys_path) as file:
        eth_keys = file.readlines()
        
    eth_addresses = list(map(lambda key: decode_eth_private_key_to_address(key.strip()), eth_keys))
    
    with open(aptos_keys_path) as file:
        lines = file.readlines()
        move_accounts = list(map(lambda key: Account.load_key(key.strip()), lines))
        move_addresses = list(map(lambda key: Account.load_key(key.strip()).address(), lines))


    assert len(move_addresses) == len(eth_addresses)

    coins_to_transfer = 10 ** 7

    idx = 0
    unsent_transactions = []
    for move_account in move_accounts:
        receiver_eth_cross = eth_addresses[idx]
        transaction_arguments = [
            TransactionArgument(bytes.fromhex(receiver_eth_cross[2:]), Serializer.to_bytes),
            TransactionArgument(coins_to_transfer, Serializer.u64),
        ]

        payload = EntryFunction.natural(
            f"{deployer_account_address}::cross_vm_coin_reverse_demo",
            "deposit",
            [TypeTag(StructTag.from_str(f"{deployer_account_address}::native_coin::DiemCoin"))],
            transaction_arguments,
        )
        unsent_transactions.append(await rest_client.create_bcs_signed_transaction(move_account, TransactionPayload(payload)))
        idx += 1
    
    await execute_batch_of_aptos_txs(rest_client=rest_client, txs=unsent_transactions)

    # print("Checking balances....")

    # portal_address = "0x5ca0f43868e106ac9aec48f8f1285896c0b9865d"
    # PortalDiem = w3.eth.contract(
    #     address=Web3.to_checksum_address(portal_address),
    #     abi=eth_coin_abi # not a mistake! mirror portal is also a ERC20
    # )

    # for eth_account in eth_addresses:
    #     balance = await PortalDiem.functions.balanceOf(eth_account).call()
    #     print(balance)
        # assert balance == top_up_to_balance


async def register_lp_tokens_uniswap_cross_experiment(
    aptos_keys_path: str
):
    print("Registering LP tokens...")
    rest_client = RestClient("http://127.0.0.1:8080/v1")
    deployer_account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
    uniswap_lp_token_address = "0x45bAAe478B597a3d1a6C90eDFBa8b52eaeAc6043"
    with open(aptos_keys_path) as file:
        lines = file.readlines()
        move_accounts = list(map(lambda key: Account.load_key(key.strip()), lines))
        move_addresses = list(map(lambda key: Account.load_key(key.strip()).address(), lines))
    
    unsent_transactions = []
    for move_account, move_address in zip(move_accounts, move_addresses):
        transaction_arguments = []

        payload = EntryFunction.natural(
            f"0x1::managed_coin",
            "register",
            [
                TypeTag(StructTag.from_str(f"{deployer_account_address}::lp_token::LPToken<{deployer_account_address}::mirror_coin::EthCoin, {deployer_account_address}::native_coin::DiemCoin>")),
            ],
            transaction_arguments,
        )
        unsent_transactions.append(await rest_client.create_bcs_signed_transaction(move_account, TransactionPayload(payload)))
    
    await execute_batch_of_aptos_txs(rest_client=rest_client, txs=unsent_transactions)
    




async def fund_npc_accounts_custom_coin_eth(
    eth_keys_path: str,  
    only_eth_coin_deployed: bool = False,
    erc_20_cross_setup: bool = False
):    
    print(f"Funding ETH accounts with custom ERC20 coin {'and approving transfer for vault' if erc_20_cross_setup else ''}...")
    genesis_eth_address = "0x14Dcb427A216216791fB63973c5b13878de30916"
    vault_address = "0x7d3d6e9f5ab582112c5cdbd712e808b2a4eafa5d"
    with open(eth_keys_path) as file:
        eth_keys = file.readlines()
        
    eth_addresses = list(map(lambda key: decode_eth_private_key_to_address(key.strip()), eth_keys))
    
    ERC20Contract = w3.eth.contract(
        address="0xcC166f312524Cc88E2c16c3bdd5735a23376B1fb" if only_eth_coin_deployed else "0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc",
        abi=eth_coin_abi
    )

    unsent_signed_txs = []
    genesis_nonce = await w3.eth.get_transaction_count(genesis_eth_address)
    top_up_to_balance = 10**18 
    for eth_key, eth_address in zip(eth_keys, eth_addresses):
        sender = "0x14Dcb427A216216791fB63973c5b13878de30916"
        receiver = eth_address

        unsent_txn = await ERC20Contract.functions.transfer(
            receiver,
            top_up_to_balance
        ).build_transaction(
            {
                "from": sender,
                'value': 0,
                'gas': 3000000,
                'chainId': 129,
                'gasPrice': 10 ** 9 + 1,
                "nonce": genesis_nonce,
            }
        )
        genesis_nonce += 1
        signed_tx = eth_sign_tx_genesis(w3, unsent_txn)
        unsent_signed_txs.append(signed_tx)

        if erc_20_cross_setup:
            unsent_txn = await ERC20Contract.functions.approve(
                Web3.to_checksum_address(vault_address),
                top_up_to_balance
            ).build_transaction(
                {
                    "from": receiver,
                    'value': 0,
                    'gas': 3000000,
                    'chainId': 129,
                    'gasPrice': 10 ** 8 + 1,
                    "nonce": 0, # assuming this is the first tx to be sent from the account
                }
            )
            signed_tx = eth_sign_tx_dynamic_pk(w3, unsent_txn, sender_pk=eth_key.strip())
            unsent_signed_txs.append(signed_tx)



    hashes = await asyncio.gather(*list(map(w3.eth.send_raw_transaction, [tx.rawTransaction for tx in unsent_signed_txs])))
    await asyncio.gather(*list(map(w3.eth.wait_for_transaction_receipt, hashes)))
    # print("Checking balances....")

    # for eth_account in eth_addresses:
    #     balance = await ERC20Contract.functions.balanceOf(eth_account).call()
    #     assert balance == top_up_to_balance

    print(f"Finished funding Ethereum accounts with custom tokens (balance {top_up_to_balance}).")



async def fund_npc_accounts_custom_coin_aptos(aptos_keys_path: str, erc_20_cross_setup: bool = False):
    print("Funding the accounts with Move custom coin...")
    config = ClientConfig()
    config.transaction_wait_in_seconds = 120
    rest_client = RestClient("http://127.0.0.1:8080/v1", client_config=config)
    faucet_client = FaucetClient("http://127.0.0.1:8081", rest_client)
    move_addresses = []
    coins_to_mint = 1000000000000000 

    with open(aptos_keys_path) as file:
        lines = file.readlines()
        move_accounts = list(map(lambda key: Account.load_key(key.strip()), lines))
        move_addresses = list(map(lambda key: Account.load_key(key.strip()).address(), lines))

    genesis_move_account = Account.load_key("0x880e2142568db71570e50ad0ce274b30c01a0b750f9aff33753fafea66c0db6f")

    print("Registering coin so that accounts can accept it..")
    payload = EntryFunction.natural(
        f"0x1::managed_coin",
        "register",
        [TypeTag(StructTag.from_str(f"{genesis_move_account.address()}::native_coin::DiemCoin"))],
        [],
    )

    txs = []
    for recipient in move_accounts:
        txs.append(await rest_client.create_bcs_signed_transaction(recipient, TransactionPayload(payload)))

    await execute_batch_of_aptos_txs(rest_client=rest_client, txs=txs)

    if erc_20_cross_setup:
        await register_mirror_eth_coin(aptos_keys_path=aptos_keys_path)

    print("Registered coins!")

    print("Minting coins to the addresses...")

    txs = []
    genesis_nonce = await rest_client.account_sequence_number(genesis_move_account.address())
    for idx, recipient in enumerate(move_addresses):
        transaction_arguments = [
            TransactionArgument(recipient, Serializer.struct),
            TransactionArgument(coins_to_mint, Serializer.u64),
        ]

        payload = EntryFunction.natural(
            f"{genesis_move_account.address()}::native_coin",
            "mint",
            [],
            transaction_arguments,
        )
        tx = await rest_client.create_bcs_signed_transaction(genesis_move_account, TransactionPayload(payload), sequence_number=genesis_nonce)
        genesis_nonce += 1
        txs.append(tx)
    
    await execute_batch_of_aptos_txs(rest_client=rest_client, txs=txs)
    print("Mint finished!")

    print("Getting balances...")
    step = 100
    for idx in range(0, len(move_addresses), step):
        aptos_balances = await asyncio.gather(
            *list(
                map(
                    rest_client.account_resource,
                    move_addresses, 
                    [f"0x1::coin::CoinStore<{genesis_move_account.address()}::native_coin::DiemCoin>"] * step
                )
            )
        )
        if idx % 200 == 0:
            print(f"Got balance for {idx} accounts")
        assert all(list(map(lambda balance: int(balance['data']['coin']['value']) == coins_to_mint, aptos_balances)))

    print(f"Funded Aptos accounts with custom coin, current balance: {aptos_balances[0]['data']['coin']['value']}")

async def fund_npc_accounts_native_coin_eth(eth_keys_path: str):
    print("Funding the accounts with ETH native coin...")
    genesis_eth_address="0x14Dcb427A216216791fB63973c5b13878de30916"
    with open(eth_keys_path) as file:
        eth_keys = file.readlines()

    eth_addresses = list(map(lambda key: decode_eth_private_key_to_address(key.strip()), eth_keys))
    
    genesis_nonce = await w3.eth.get_transaction_count(genesis_eth_address)
    unsent_signed_txs = []
    balance = 1000 * 10 ** 18

    for address in eth_addresses:
        unsent_txn = {
            'from': genesis_eth_address,
            'chainId': 129,
            'to': Address(HexBytes(address)),
            'value': balance,
            'nonce': genesis_nonce,
            'gas': 21001,
            'gasPrice': 10 ** 9 + 1,
        }
        genesis_nonce +=  1

        signed_tx = eth_sign_tx_genesis(
            w3=w3, 
            unsent_tx=unsent_txn
        )
        unsent_signed_txs.append(signed_tx)

    # print(datetime.datetime.now())
    hashes = await asyncio.gather(*list(map(w3.eth.send_raw_transaction, [tx.rawTransaction for tx in unsent_signed_txs])))
    # print(datetime.datetime.now())
    # tx_hash = await w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    await asyncio.gather(*list(map(w3.eth.wait_for_transaction_receipt, hashes)))
    print("Checking balances...")
    balances = await asyncio.gather(*list(map(w3.eth.get_balance, eth_addresses)))
    assert all(list(map(lambda account_balance: account_balance == balance, balances)))
    print(f"Funded Ethereum accounts with balance of {balance}!")
    
    print("Finished funding Ethereum accounts!")


async def fund_npc_accounts_native_coin_aptos(aptos_keys_path: str):
    print("Funding the accounts with Move native coin...")
    rest_client = RestClient("http://127.0.0.1:8080/v1")
    faucet_client = FaucetClient("http://127.0.0.1:8081", rest_client)
    move_addresses = []
    balance = 9999999999999
    with open(aptos_keys_path) as file:
        move_addresses = list(map(lambda key: Account.load_key(key.strip()).address(), file.readlines()))

    step = 100
    for idx in range(0, len(move_addresses), step):
        await asyncio.gather(*list(map(faucet_client.fund_account, move_addresses[idx:idx+step], [balance] * step))) 
        if idx % 200 == 0:
            print(f"Funded {idx} accounts")

    print("Checking balances...")

    step = 100
    for idx in range(0, len(move_addresses), step):
        balances =  await asyncio.gather(*list(map(rest_client.account_balance, move_addresses[idx:idx+step]))) 
        if idx % 200 == 0:
            print(f"Got balance of {idx} accounts")
        assert all(list(map(lambda x: x == balance, balances)))

    print(f"Funded Aptos accounts with {balance} tokens!")