
from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.type_tag import TypeTag, StructTag

from patched_aptos_sdk import LIDLPatchedAptosSDK
from utils import aptos_write_tx_to_file

from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction, TransactionArgument

cli_account = Account.load_key("0x880e2142568db71570e50ad0ce274b30c01a0b750f9aff33753fafea66c0db6f")

account_address = "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
coin_wrapper_address = account_address

cross_compound_wrapper_address = bytes.fromhex("812cBBdE09AF8214a5c3addE18Fcec9891196494")
print(cross_compound_wrapper_address)

payload_borrow = EntryFunction.natural(
    f"{coin_wrapper_address}::cross_vm_coin_compound",
    "deposit_collateral_and_borrow",
    [
        TypeTag(StructTag.from_str(f"{account_address}::native_coin::DiemCoin")),
        TypeTag(StructTag.from_str(f"{account_address}::mirror_coin::EthCoin"))
    ],
    [
        TransactionArgument(5 * 10**8, Serializer.u64)
    ],
)

payload_repay = EntryFunction.natural(
    f"{coin_wrapper_address}::cross_vm_coin_compound",
    "repay_debt_and_fetch_collateral",
    [
        TypeTag(StructTag.from_str(f"{account_address}::native_coin::DiemCoin")),
        TypeTag(StructTag.from_str(f"{account_address}::mirror_coin::EthCoin"))
    ],
    [
        TransactionArgument(200000, Serializer.u64)
    ],
)

sdk = LIDLPatchedAptosSDK() # custom sdk to create transactions with sequential nonces inside the script

with open("./compound_cross_100k.txt", "wb") as file:
    print("Writing txs...")
    for i in range(0, 10**5 // 2):
        tx_1: SignedTransaction = sdk.create_bcs_signed_transaction(cli_account, TransactionPayload(payload_borrow))
        aptos_write_tx_to_file(file, tx_1)
        print("borrow")
        tx_2: SignedTransaction = sdk.create_bcs_signed_transaction(cli_account, TransactionPayload(payload_repay))
        aptos_write_tx_to_file(file, tx_2)
        print("repay")