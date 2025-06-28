import time
from typing import Dict

import httpx
from aptos_sdk.account import Account
from aptos_sdk.account_address import AccountAddress
from aptos_sdk.authenticator import Authenticator, Ed25519Authenticator
from aptos_sdk.async_client import ApiError
from aptos_sdk.transactions import TransactionPayload, SignedTransaction, RawTransaction


class LIDLPatchedAptosSDK:
    client = httpx.Client()
    base_url = "http://127.0.0.1:8080/v1"
    current_nonce = -1
    logger_on = True

    def account_sequence_number(
        self,
        account_address: AccountAddress,
        ledger_version: int = None
    ) -> int:
        if self.current_nonce < 0:
            account_res = self.account(account_address, ledger_version)
            self.current_nonce = int(account_res["sequence_number"])
            print(f"Creating tx with nonce {int(account_res['sequence_number'])}")
            return int(account_res["sequence_number"])
        else:
            self.current_nonce += 1
            print(f"Creating tx with nonce {self.current_nonce}")
            return self.current_nonce

    def account(
            self,
            account_address: AccountAddress,
            ledger_version: int = None
    ) -> Dict[str, str]:
        """Returns the sequence number and authentication key for an account"""

        if not ledger_version:
            request = f"{self.base_url}/accounts/{account_address}"
        else:
            request = f"{self.base_url}/accounts/{account_address}?ledger_version={ledger_version}"

        response = self.client.get(request)
        if response.status_code >= 400:
            raise ApiError(f"{response.text} - {account_address}", response.status_code)
        return response.json()

    def create_bcs_transaction(
            self,
            sender: Account,
            payload: TransactionPayload,
     ) -> RawTransaction:
        return RawTransaction(
            sender=sender.address(),
            sequence_number=self.account_sequence_number(sender.address()),
            payload=payload,
            max_gas_amount=100_000,
            gas_unit_price=100,
            expiration_timestamps_secs=int(time.time()) + 60 * 60 * 24 * 10000000,
            chain_id=4,
        )

    def create_bcs_signed_transaction(
            self,
            sender: Account,
            payload: TransactionPayload,
    ) -> SignedTransaction:
        raw_transaction = self.create_bcs_transaction(sender, payload)
        signature = sender.sign(raw_transaction.keyed())
        authenticator = Authenticator(
            Ed25519Authenticator(sender.public_key(), signature)
        )
        return SignedTransaction(raw_transaction, authenticator)