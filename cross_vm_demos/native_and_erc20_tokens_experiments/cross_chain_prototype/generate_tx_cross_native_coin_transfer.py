import sys

from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag

sys.path.insert(1, '/home/vladyslav/PycharmProjects/cross-vm-contracts')

from utils_aptos import LIDLAptosSDK

# from move_scripts.balance_of import get_balance

from utils_aptos import aptos_write_tx_to_file
from aptos_sdk.async_client import FaucetClient, RestClient
from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument

rest_client = RestClient("http://127.0.0.1:8080/v1")
faucet_client = FaucetClient("http://127.0.0.1:8081/", rest_client)

K = 1000
num_of_txs = 100 * K

cli_account = Account.load_key("0x880e2142568db71570e50ad0ce274b30c01a0b750f9aff33753fafea66c0db6f")
account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"


some_eth_address = bytes.fromhex("d9B7259408e8e176A85E1033367a4365aDF2F3CF")

transaction_arguments = [
    TransactionArgument(some_eth_address, Serializer.to_bytes),
    TransactionArgument(10, Serializer.u64),
]

payload = EntryFunction.natural(
    f"{account_address}::cross_vm_coin_erc20",
    "deposit_aptos_coin",
    [],
    transaction_arguments,
)

sdk = LIDLAptosSDK() # custom sdk to create transactions with sequential nonces inside the script

with open("./transaction_batches/move_native_token_cross_100k.txt", "wb") as file:
    print("Writing txs...")
    for i in range(0, num_of_txs):
        tx_1: SignedTransaction = sdk.create_bcs_signed_transaction(cli_account, TransactionPayload(payload))
        aptos_write_tx_to_file(file, tx_1)