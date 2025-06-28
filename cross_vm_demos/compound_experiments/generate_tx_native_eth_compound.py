import concurrent
from time import perf_counter

from eth_typing import Address
from hexbytes import HexBytes
from typing_extensions import Tuple
from web3 import Web3

from abis import my_contract_abi, faucet_token_abi, faucet_token_2_abi, cerc20_abi
from utils import eth_sign_tx

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

num_of_txs = 10 ** 5


def generate_txs():
    deployer = "0x14Dcb427A216216791fB63973c5b13878de30916"
    with open("./compound_intra_100k.txt", "wb") as f:
        generate_and_write_txs_parallel(f, deployer)


def generate_and_write_txs_parallel(f, public_address_of_senders_account):
    next_nonce = w3.eth.get_transaction_count(public_address_of_senders_account)
    tx_nonces = [(next_nonce, i) for i in range(0, 100000)]

    t1_start = perf_counter()
    with concurrent.futures.ProcessPoolExecutor(8) as executor:
        result = list(executor.map(generate_transactions_parallel, tx_nonces))
        result.sort(key=lambda x: x[0])
        for (nonce, signed_tx) in result:
            tx_bytes = bytes.fromhex(signed_tx.rawTransaction.hex()[2:])
            length_of_tx = len(tx_bytes)
            f.write(length_of_tx.to_bytes(2, byteorder='little'))
            f.write(tx_bytes)
    t1_stop = perf_counter()
    print("Elapsed time during the whole program in seconds:", t1_stop - t1_start)


def generate_transactions_parallel(nonce: Tuple[int, int]):
    if nonce[1] % 2 == 0:
        return nonce[0] + nonce[1], generate_borrow_tx(nonce[0] + nonce[1])
    else:
        return nonce[0] + nonce[1], generate_repay_tx(nonce[0] + nonce[1])


def generate_borrow_tx(current_txs: int):
    deployer = "0x14Dcb427A216216791fB63973c5b13878de30916"
    amount_to_supply_as_collateral = 10 ** 13
    MyContract = w3.eth.contract(
        address=Address(HexBytes("0xcc166f312524cc88e2c16c3bdd5735a23376b1fb")),
        abi=my_contract_abi
    )
    FaucetToken = w3.eth.contract(
        address=Address(HexBytes("0x63b5dc8063ebb9ba9e05d74ec48b8c570f7624cc")),
        abi=faucet_token_abi
    )
    FaucetToken2 = w3.eth.contract(
        address=Address(HexBytes("0x812cbbde09af8214a5c3adde18fcec9891196494")),
        abi=faucet_token_2_abi
    )
    CERC20_FaucetToken = w3.eth.contract(
        address=Address(HexBytes("0x866a4a061de0f196205dff79b3c47700b570f617")),
        abi=cerc20_abi
    )
    CERC20_FaucetToken2 = w3.eth.contract(
        address=Address(HexBytes("0x14529a6c979b2563207e260a6138f4026b19ee0d")),
        abi=cerc20_abi
    )
    # tx = await MyContract.borrowEthExample(
    #    contractAddress.CErc20Twin,
    #    contractAddress.CErc20,
    #    contractAddress.FaucetToken,
    #    amt_to_supply
    #  );
    # borrowEthExmaple = borrow tokens; TODO(!!!!!!!!!): refactor the names (breaks ABIs)
    unsent_txn = MyContract.functions.borrowEthExample(
        CERC20_FaucetToken2.address,
        CERC20_FaucetToken.address,
        FaucetToken.address,
        amount_to_supply_as_collateral
    ).build_transaction(
        {
            "from": deployer,
            'value': 0,
            'gas': 30000000,
            'gasPrice': 1,
            "nonce": current_txs,
        }
    )
    print(f"Generated borrow tx with nonce {current_txs}")
    signed_tx = eth_sign_tx(w3, unsent_txn)
    return signed_tx


def generate_repay_tx(
    current_txs: int,
):
    deployer = "0x14Dcb427A216216791fB63973c5b13878de30916"
    amount_to_repay = 2 * 10 ** 15
    MyContract = w3.eth.contract(
        address=Address(HexBytes("0xcc166f312524cc88e2c16c3bdd5735a23376b1fb")),
        abi=my_contract_abi
    )
    FaucetToken = w3.eth.contract(
        address=Address(HexBytes("0x63b5dc8063ebb9ba9e05d74ec48b8c570f7624cc")),
        abi=faucet_token_abi
    )
    FaucetToken2 = w3.eth.contract(
        address=Address(HexBytes("0x812cbbde09af8214a5c3adde18fcec9891196494")),
        abi=faucet_token_2_abi
    )
    CERC20_FaucetToken = w3.eth.contract(
        address=Address(HexBytes("0x866a4a061de0f196205dff79b3c47700b570f617")),
        abi=cerc20_abi
    )
    CERC20_FaucetToken2 = w3.eth.contract(
        address=Address(HexBytes("0x14529a6c979b2563207e260a6138f4026b19ee0d")),
        abi=cerc20_abi
    )
    # tx = await MyContract.myEthRepayBorrow(
    #     contractAddress.CErc20Twin,
    #     contractAddress.CErc20,
    #     FaucetToken2.address,
    #     borrowBalanceStored,
    #     {gasLimit: 30000000},
    # );
    #  myEthRepayBorrow() = repay borrow; TODO: fix naming
    unsent_txn = MyContract.functions.myEthRepayBorrow(
        CERC20_FaucetToken2.address,
        CERC20_FaucetToken.address,
        FaucetToken2.address,
        amount_to_repay
    ).build_transaction(
        {
            "from": deployer,
            'value': 0,
            'gas': 30000000,
            'gasPrice': 1,
            "nonce": current_txs,
        }
    )
    print(f"Generated repay tx with nonce {current_txs}")
    signed_tx = eth_sign_tx(w3, unsent_txn)
    return signed_tx


if __name__ == "__main__":
    generate_txs()