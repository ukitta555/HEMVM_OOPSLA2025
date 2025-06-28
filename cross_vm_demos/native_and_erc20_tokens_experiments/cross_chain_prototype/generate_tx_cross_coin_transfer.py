

from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag

from utils_aptos import LIDLAptosSDK
from utils_aptos import aptos_write_tx_to_file
from aptos_sdk.async_client import FaucetClient, RestClient
from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument

rest_client = RestClient("http://127.0.0.1:8080/v1")
faucet_client = FaucetClient("http://127.0.0.1:8081/", rest_client)

num_of_txs = 10 ** 5


cli_account = Account.load_key("0x880e2142568db71570e50ad0ce274b30c01a0b750f9aff33753fafea66c0db6f")
account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"


proxy_address = bytes.fromhex("cC166f312524Cc88E2c16c3bdd5735a23376B1fb")

transaction_arguments = [
    TransactionArgument(proxy_address, Serializer.to_bytes),
    TransactionArgument(100, Serializer.u64),
]

payload = EntryFunction.natural(
    f"0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06::cross_vm_coin_erc20",
    "deposit",
    [TypeTag(StructTag.from_str(f"{account_address}::native_coin::DiemCoin"))],
    transaction_arguments,
)

sdk = LIDLAptosSDK() # custom sdk to create transactions with sequential nonces inside the script

with open("move_coin_cross_100k.txt", "wb") as file:
    print("Writing txs...")
    for i in range(0, num_of_txs):
        tx_1: SignedTransaction = sdk.create_bcs_signed_transaction(cli_account, TransactionPayload(payload))
        aptos_write_tx_to_file(file, tx_1)