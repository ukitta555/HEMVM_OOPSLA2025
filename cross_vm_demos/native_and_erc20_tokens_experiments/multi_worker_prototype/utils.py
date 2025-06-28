import enum
import time
from typing import Dict

import httpx
from aptos_sdk.account import Account
from aptos_sdk.account_address import AccountAddress
from aptos_sdk.async_client import ApiError
from aptos_sdk.authenticator import Authenticator, Ed25519Authenticator
from aptos_sdk.transactions import TransactionPayload, SignedTransaction, RawTransaction
from eth_account import Account as EthAccount
import secrets

from web3 import Web3


class LIDLAptosSDK:
    client = httpx.Client()
    base_url = "http://127.0.0.1:8080/v1"
    current_nonce: dict[str, int]
    logger_on = True
    
    def __init__(self):
        self.current_nonce = dict()

    def account_sequence_number(
            self,
            account_address: AccountAddress,
            ledger_version: int = None
    ) -> int:
        if self.current_nonce.get(str(account_address)) is None:
            account_res = self.account(account_address, ledger_version)
            self.current_nonce[str(account_address)] = int(account_res["sequence_number"])
            # print(f"Creating tx with nonce {int(account_res['sequence_number'])} for account {account_address}")
            return int(account_res["sequence_number"])
        else:
            self.current_nonce[str(account_address)] += 1
            # print(f"Creating tx with nonce {self.current_nonce[str(account_address)]} for account {account_address}")
            return self.current_nonce[str(account_address)]

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
    

class TxType(enum.Enum):
    NATIVE_APTOS_TX = 1
    CROSS_APTOS_TX = 3
    NATIVE_ETH_TX = 5
    CROSS_ETH_TX = 7

def write_tx_to_file_with_tx_type(file, unsent_signed_txn, tx_type: TxType):
    tx_bytes = None
    if tx_type == TxType.NATIVE_APTOS_TX or tx_type == TxType.CROSS_APTOS_TX:
        tx_bytes = unsent_signed_txn.bytes() # Aptos tx case
    else:
        tx_bytes = bytes.fromhex(unsent_signed_txn.rawTransaction.hex()[2:]) # Eth tx case
    length_of_tx_type = 1
    total_length = len(tx_bytes) + length_of_tx_type
    file.write(total_length.to_bytes(2, byteorder='little'))
    file.write(tx_bytes)
    print(f"Transaction type: {tx_type}")
    # print(f"Transaction type encoding: {tx_type.value}")
    file.write(tx_type.value.to_bytes(1, byteorder='little'))


def eth_sign_tx_genesis(w3: Web3, unsent_tx):
    return w3.eth.account.sign_transaction(
        unsent_tx,
        private_key="fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa",
    )

def eth_sign_tx_dynamic_pk(w3: Web3, unsent_tx, sender_pk: str):
    return w3.eth.account.sign_transaction(
        unsent_tx,
        private_key=sender_pk
    )


def eth_sign_and_write_tx_to_file_no_padding(w3, file, unsent_txn):
    signed_tx = w3.eth.account.sign_transaction(
        unsent_txn,
        private_key="fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa",
    )

    tx_bytes = bytes.fromhex(signed_tx.rawTransaction.hex()[2:])
    length_of_tx = len(tx_bytes)
    file.write(length_of_tx.to_bytes(2, byteorder='little'))
    file.write(tx_bytes)

def aptos_write_tx_to_file_no_padding(file, unsent_signed_txn: SignedTransaction):
    tx_bytes = unsent_signed_txn.bytes()
    length_of_tx = len(tx_bytes)
    file.write(length_of_tx.to_bytes(2, byteorder='little'))
    file.write(tx_bytes)

def generate_aptos_keys(num_of_accounts):
    with open("../../experiment_runner/keys/private_keys_aptos.txt", "w") as file:
        for idx in range(num_of_accounts):
            account = Account.generate()
            file.write(str(account.private_key) + ("\n" if idx < num_of_accounts - 1 else ""))

def generate_eth_keys(num_of_accounts):
    with open("../../experiment_runner/keys/private_keys_ethereum.txt", "w") as file:
        for idx in range(num_of_accounts):
            priv = secrets.token_hex(32)
            private_key = "0x" + priv
            file.write(private_key + ("\n" if idx < num_of_accounts - 1 else ""))        

def decode_eth_private_key_to_address(private_key):
    return EthAccount.from_key(private_key).address

def read_eth_keys():
    eth_private_keys = None
    with open("./../../experiment_runner/keys/private_keys_ethereum.txt", "r") as eth_pk_file:
        eth_private_keys = list(map(lambda x: x.strip(), eth_pk_file.readlines()))
    return eth_private_keys

def read_move_keys():
    move_private_keys = None
    with open("./../../experiment_runner/keys/private_keys_aptos.txt", "r") as aptos_pk_file:
        move_private_keys = list(map(lambda x: x.strip(), aptos_pk_file.readlines()))
    return move_private_keys


def cache_of_eth_addresses(eth_private_keys: list[str]) -> dict:
    eth_addresses = dict()
    for eth_key in eth_private_keys:
        eth_addresses[eth_key] = decode_eth_private_key_to_address(eth_key)
    return eth_addresses

def cache_of_move_accounts(move_private_keys: list[str]) -> dict:
    move_accounts = dict()
    for move_key in move_private_keys:
        move_accounts[move_key] = Account.load_key(move_key)
    return move_accounts
    


if __name__ == "__main__":
    generate_eth_keys(num_of_accounts=200)
    generate_aptos_keys(num_of_accounts=200)