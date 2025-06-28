from typing import BinaryIO
from eth_typing import Address
from hexbytes import HexBytes
from web3 import Web3
from utils import eth_sign_and_write_tx_to_file

w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

# 0xae145b1bf5e1bd05e47096283b1e6dcf114f954aa29d2b8689c5fa749ab612bc last tx hash
# 0x4339eda97b264c97c36446547f881c42645f466513707c89303838438f33a746 first tx hash
# ~tx 600 0x5fce0023381547110d1d4e830ce224ab8b81cc5265d2d09df1a60e862781767b

# block_data = w3.cfx.get_block(1)
print(w3.eth.get_transaction_receipt(
    transaction_hash=HexBytes("0x5593f6b23a967ad5da2c33f3f6fba466102ffb9dbe0f069cc7778d89caa76aa7"),
))


# w3.cfx.send_transaction({
#     'to': w3.address.zero_address(),
#     'value': 10**18,
# }).executed()