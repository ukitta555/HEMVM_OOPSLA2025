#!/usr/bin/env python3
"""
CLI script for measuring transaction receipt wait times for different transaction types.
"""

import argparse
import sys
from time import perf_counter

import cfx_account
from cfx_account import LocalAccount
from cfx_address import Base32Address
from conflux_web3 import Web3


def setup_web3_and_accounts():
    """Setup Web3 connection and accounts."""
    w3 = Web3(Web3.HTTPProvider("http://localhost:12537"))
    
    # cfxtest:aamr3rbhyjncc36v9rv3stc5csd2522kc2v4d1vp1u
    acct: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa")
    # cfxtest:aaru08p73np1gm9hbvm4gk8y8ue10m4pe62vc4ap4k
    acct2: LocalAccount = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafb")
    
    print(f"Account 1: {acct.address}, Balance: {w3.cfx.get_balance(acct.address).value / 10 ** 18} CFX")
    print(f"Account 2: {acct2.address}")
    w3.cfx.default_account = acct
    
    return w3, acct, acct2


def get_transaction_hashes(mode):
    """Get transaction hashes based on the specified mode."""
    hashes = {
        "erc20": {
            "first": "0x6fd3211ebbfa9e85edeef993cf5d8f7f8ed818a3edf1ee152c11a485b92d87b0",
            "last": "0xdaf37d94170eff61c2b530c8067e56fad435a7c5e3348189adaf5d8516aab34a"
        },
        "native": {
            "first": "0x4339eda97b264c97c36446547f881c42645f466513707c89303838438f33a746",
            "last": "0xae145b1bf5e1bd05e47096283b1e6dcf114f954aa29d2b8689c5fa749ab612bc"
        },
        "cross-native": {
            "first": "0xb31579694b422c5d605e4ed6067ec189fc382500b04575911ccf5fed04210fb7",
            "last": "0x0070bfb4d2809d3ce299b98c9102b16867052867587d36988b60d844fd625128"
        },
        "cross-erc20": {
            "first": "0x31dda79e420455d76a0390392ab704b232a38f5c0492cdba2a3b61fa7d8bc97e",
            "last": "0xd693e485244c7b8db1ea53ec21c76c3842ddd7f65abf1d00bee685128ea7bbd3"
        }
    }
    return hashes.get(mode)


def run_measurement(w3, mode):
    """Run the transaction receipt wait time measurement."""
    hashes = get_transaction_hashes(mode)
    if not hashes:
        print(f"Error: Unknown mode '{mode}'")
        return
    
    
    print(f"\n=== {mode.upper()} Transaction Measurement ===")
    print(f"Using first hash: {hashes['first']}")
    
    # First, wait for the first transaction to ensure it's processed
    print("Waiting for first transaction to be processed...")
    w3.cfx.wait_for_transaction_receipt(
        transaction_hash=hashes["first"],
        timeout=400,
        poll_latency=0.05
    )
    print(f"First transaction processed: {w3.cfx.get_transaction_by_hash(hashes['first'])}")
    


    # Measure the target transaction
    print(f"Measuring wait time for transaction: {hashes['last']}")
    t1_start = perf_counter()
    
    w3.cfx.wait_for_transaction_receipt(
        transaction_hash=hashes["last"],
        timeout=400,
        poll_latency=0.05
    )
    
    t1_stop = perf_counter()
    
    # Get transaction details
    tx_details = w3.cfx.get_transaction_by_hash(hashes['last'])
    print(f"Transaction details: {tx_details}")
    
    elapsed_time = t1_stop - t1_start
    print(f"Elapsed time for {mode} transaction: {elapsed_time:.4f} seconds")
    
    return elapsed_time


def main():
    parser = argparse.ArgumentParser(
        description="Measure transaction receipt wait times for different transaction types",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python time_measurement_for_sync_api_handlers.py erc20
  python time_measurement_for_sync_api_handlers.py native
  python time_measurement_for_sync_api_handlers.py cross-native
  python time_measurement_for_sync_api_handlers.py cross-erc20
        """
    )
    
    parser.add_argument(
        "mode",
        choices=["erc20", "native", "cross-native", "cross-erc20"],
        help="Transaction type to measure"
    )
    
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=400,
        help="Timeout for transaction receipt wait (default: 400)"
    )
    
    parser.add_argument(
        "--poll-latency",
        type=float,
        default=0.05,
        help="Poll latency for transaction receipt wait (default: 0.05)"
    )
    
    args = parser.parse_args()
    
    try:
        # Setup Web3 and accounts
        w3, acct, acct2 = setup_web3_and_accounts()
        
        # Run the measurement
        elapsed_time = run_measurement(w3, args.mode)
        
        if elapsed_time is not None:
            print(f"\nFinal balance for {acct.address}: {w3.cfx.get_balance(acct.address).to('CFX')}")
            print(f"Measurement completed successfully!")
        
    except KeyboardInterrupt:
        print("\nMeasurement interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during measurement: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()