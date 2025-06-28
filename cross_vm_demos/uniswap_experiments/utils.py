from aptos_sdk.transactions import SignedTransaction


def eth_sign_and_write_tx_to_file(w3, file, unsent_txn):
    signed_tx = w3.eth.account.sign_transaction(
        unsent_txn,
        private_key="fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa",
    )

    tx_bytes = bytes.fromhex(signed_tx.rawTransaction.hex()[2:])
    length_of_tx = len(tx_bytes)
    file.write(length_of_tx.to_bytes(2, byteorder='little'))
    file.write(tx_bytes)

def eth_sign_tx(w3, unsent_tx):
    return w3.eth.account.sign_transaction(
        unsent_tx,
        private_key="fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa",
    )


def aptos_write_tx_to_file(file, unsent_signed_txn: SignedTransaction):
    tx_bytes = unsent_signed_txn.bytes()
    length_of_tx = len(tx_bytes)
    file.write(length_of_tx.to_bytes(2, byteorder='little'))
    file.write(tx_bytes)
