import conflux_web3
from cfx_account import LocalAccount


def cfx_sign_and_write_tx_to_file(
        sender: LocalAccount,
        file,
        unsent_txn
):
    signed_tx = sender.sign_transaction(unsent_txn)
    print(f"Hash {signed_tx.hash.hex()}")
    tx_bytes = bytes.fromhex(signed_tx.rawTransaction.hex()[2:])
    length_of_tx = len(tx_bytes)
    file.write(length_of_tx.to_bytes(2, byteorder='little'))
    file.write(tx_bytes)
