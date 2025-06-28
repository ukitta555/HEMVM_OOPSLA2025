#!/usr/bin/env python

from common import rest_client
from aptos_sdk.account import Account

cli_account = Account.load_key("0x880e2142568db71570e50ad0ce274b30c01a0b750f9aff33753fafea66c0db6f")
cli_account_2 = Account.load_key("0x86b94222e0e35d40f8c54f398dce41f89203708ffc18fbc0e3cf0edbf75b00c3")

# cli_address = cli_account.account_address

balance = rest_client.account_balance(cli_account.address())
print(f"{cli_account.address().hex()} balance is {int(balance)/1e8}.")

balance = rest_client.account_balance(cli_account_2.address())
print(f"{cli_account_2.address().hex()} balance is {int(balance)/1e8}.")