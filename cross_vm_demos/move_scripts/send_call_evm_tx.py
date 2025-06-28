import sys

sys.path.insert(1, '/home/vladyslav/PycharmProjects/cross-vm-contracts')

from uniswap_experiments.utils import aptos_write_tx_to_file

from common import rest_client, cli_account
from aptos_sdk.transactions import EntryFunction, TransactionPayload, SignedTransaction

payload = EntryFunction.natural(
            f"0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06::caller",
            "call",
            [],
            [])
tx_1: SignedTransaction = rest_client.create_bcs_signed_transaction(cli_account, TransactionPayload(payload))
tx_2: SignedTransaction = rest_client.create_bcs_signed_transaction(cli_account, TransactionPayload(payload))
with open("compound_cross_100k.txt", "wb") as file:
    print("Writing txs...")
    aptos_write_tx_to_file(file, tx_1)
    aptos_write_tx_to_file(file, tx_2)
# tx_hash = rest_client.submit_bcs_transaction(tx)
# rest_client.wait_for_transaction(tx_hash)