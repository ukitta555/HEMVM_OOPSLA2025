from common import rest_client, cli_account
from aptos_sdk.transactions import EntryFunction, TransactionPayload

payload = EntryFunction.natural(
            f"0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06::caller",
            "transfer",
            [],
            [])
tx = rest_client.create_bcs_signed_transaction(cli_account, TransactionPayload(payload))
tx_hash = rest_client.submit_bcs_transaction(tx)
rest_client.wait_for_transaction(tx_hash)

balance = rest_client.account_balance(cli_account.address())
print(f"Sender balance in Move Space is {int(balance)/1e8}.")