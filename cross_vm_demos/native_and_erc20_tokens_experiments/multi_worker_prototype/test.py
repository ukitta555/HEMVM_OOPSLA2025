# from eth_typing import Address
# from hexbytes import HexBytes
# from web3 import Web3
# from abis import proxy_abi
# from utils import eth_sign_tx

# w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

# num_of_txs = 10 ** 5

# #  (String) Vault address
# #  (Hex) 0x7d3d6e9f5ab582112c5cdbd712e808b2a4eafa5d
# #  (String) Mirror address
# #  (Hex) 0x5ca0f43868e106ac9aec48f8f1285896c0b9865d

# def send_tx():
#     sender = "0x14Dcb427A216216791fB63973c5b13878de30916"
#     receiver = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
#     nonce = w3.eth.get_transaction_count(sender)
#     ProxyERC20 = w3.eth.contract(
#         address=Address(HexBytes("0xcC166f312524Cc88E2c16c3bdd5735a23376B1fb")),
#         abi=proxy_abi
#     )
#     unsent_txn = ProxyERC20.functions \
#         .sendETHCrossSpace(HexBytes(receiver)) \
#         .build_transaction(
#             {
#                 "from": sender,
#                 'value': 10 ** 18,
#                 'gas': 3000000,
#                 'gasPrice': 10 ** 13 + 1,
#                 "nonce": nonce,
#             }
#         )
#     print(f"Generated deposit tx with nonce {nonce}")
#     signed_tx = eth_sign_tx(w3, unsent_txn)
#     output = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
#     print(output)
#     # return nonce, signed_tx

# if __name__ == "__main__":
#     send_tx()



import sys

from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag

sys.path.insert(1, '/home/vladyslav/PycharmProjects/cross-vm-contracts')

from native_and_erc20_tokens_experiments.multi_worker_prototype.utils import LIDLAptosSDK, TxType, write_tx_to_file_with_tx_type

# from move_scripts.balance_of import get_balance

from aptos_sdk.async_client import FaucetClient, RestClient
from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument

rest_client = RestClient("http://127.0.0.1:8080/v1")
faucet_client = FaucetClient("http://127.0.0.1:8081/", rest_client)


cli_account = Account.load_key("0x880e2142568db71570e50ad0ce274b30c01a0b750f9aff33753fafea66c0db6f")
account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"


proxy_address = bytes.fromhex("cC166f312524Cc88E2c16c3bdd5735a23376B1fb")

transaction_arguments = [
    TransactionArgument(proxy_address, Serializer.to_bytes),
    TransactionArgument(10 ** 4, Serializer.u64),
]

payload = EntryFunction.natural(
    f"{account_address}::cross_vm_coin_erc20",
    "deposit_aptos_coin",
    [],
    transaction_arguments,
)

sdk = LIDLAptosSDK() # custom sdk to create transactions with sequential nonces inside the script


with open("./transaction_batches/test.txt", "wb") as file:
    print("Writing cross txs...")
    for i in range(0, 10 ** 5):
        tx_cross: SignedTransaction = sdk.create_bcs_signed_transaction(cli_account, TransactionPayload(payload))
        write_tx_to_file_with_tx_type(file, tx_cross, TxType.CROSS_APTOS_TX)


# cli_account = Account.load_key("0x880e2142568db71570e50ad0ce274b30c01a0b750f9aff33753fafea66c0db6f")
# cli_account_2 = Account.load_key("0x86b94222e0e35d40f8c54f398dce41f89203708ffc18fbc0e3cf0edbf75b00c3")


# transaction_arguments = [
#     TransactionArgument(cli_account_2.address(), Serializer.struct),
#     TransactionArgument(10**4, Serializer.u64),
# ]

# payload = EntryFunction.natural(
#     f"{account_address}::native_coin",
#     "transfer",
#     [],
#     transaction_arguments,
# )


# with open("./transaction_batches/test.txt", "ab") as file:
#     print("Writing native txs...")
#     for i in range(0, 10**5):
#         tx_native: SignedTransaction = sdk.create_bcs_signed_transaction(cli_account, TransactionPayload(payload))
#         aptos_write_tx_to_file_with_tx_type(file, tx_native, TxType.NATIVE_APTOS_TX)


