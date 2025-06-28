from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag

from move_helpers import LIDLAptosSDK

from utils import aptos_write_tx_to_file

from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument

num_of_txs = 10 ** 5

cli_account = Account.load_key("0x880e2142568db71570e50ad0ce274b30c01a0b750f9aff33753fafea66c0db6f")
cli_address = cli_account.account_address

account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
coin_wrapper_address = account_address
cross_uniswap_wrapper_address = bytes.fromhex("812cBBdE09AF8214a5c3addE18Fcec9891196494")
print(cross_uniswap_wrapper_address)

payload = EntryFunction.natural(
    f"{coin_wrapper_address}::cross_vm_coin_reverse_demo",
    "swap_exact_tokens_for_tokens",
    [
        TypeTag(StructTag.from_str(f"{account_address}::native_coin::DiemCoin")),
        TypeTag(StructTag.from_str(f"{account_address}::mirror_coin::EthCoin"))
    ],
    [
        TransactionArgument(1000 * 10**3, Serializer.u64),
        TransactionArgument(1, Serializer.u64),
        TransactionArgument(1913334000, Serializer.u64),
        TransactionArgument(cross_uniswap_wrapper_address, Serializer.to_bytes)
    ],
)

sdk = LIDLAptosSDK() # custom sdk to create transactions with sequential nonces inside the script

with open("uniswap_cross_100k.txt", "wb") as file:
    print("Writing txs...")
    for i in range(0, num_of_txs):
        tx_1: SignedTransaction = sdk.create_bcs_signed_transaction(cli_account, TransactionPayload(payload))
        aptos_write_tx_to_file(file, tx_1)