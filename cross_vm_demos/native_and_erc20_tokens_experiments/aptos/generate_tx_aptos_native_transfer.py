import sys

from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag

sys.path.insert(1, '/home/vladyslav/PycharmProjects/cross-vm-contracts')

from utils_aptos import LIDLAptosSDK

# from move_scripts.balance_of import get_balance
from aptos_sdk.async_client import FaucetClient, RestClient
from utils_aptos import aptos_write_tx_to_file

from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument

rest_client = RestClient("http://127.0.0.1:8080/v1")
faucet_client = FaucetClient("http://127.0.0.1:8081/", rest_client)

bob = Account.generate()

cli_account = Account.load_key("0x880e2142568db71570e50ad0ce274b30c01a0b750f9aff33753fafea66c0db6f")
cli_account_2 = Account.load_key("0x86b94222e0e35d40f8c54f398dce41f89203708ffc18fbc0e3cf0edbf75b00c3")


# account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
# router_address = "0x7a526ec5f06a7976caec96614f0db691f53b452424a3897a18a115ddd300c110"
#
# get_balance(f"{account_address}::native_coin::DiemCoin", account_address)
# get_balance(f"{account_address}::native_coin_2::DiemCoin2", account_address)

transaction_arguments = [
    TransactionArgument(cli_account_2.address(), Serializer.struct),
    TransactionArgument(10**2, Serializer.u64),
]

payload = EntryFunction.natural(
    "0x1::coin",
    "transfer",
    [TypeTag(StructTag.from_str(f"0x1::aptos_coin::AptosCoin"))],
    transaction_arguments,
)

sdk = LIDLAptosSDK() # custom sdk to create transactions with sequential nonces inside the script

with open("move_native_token_intra_100k.txt", "wb") as file:
    print("Writing txs...")
    for i in range(0, 10**5):
        tx_1: SignedTransaction = sdk.create_bcs_signed_transaction(cli_account, TransactionPayload(payload))
        aptos_write_tx_to_file(file, tx_1)