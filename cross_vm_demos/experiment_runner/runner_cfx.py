#!/usr/bin/env python3
"""
CLI script for running experiments on EVoM-cfx-rust-oopsla24.
"""

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from time import perf_counter

import requests
from conflux_web3 import Web3


def setup_web3_and_accounts():
    """Setup Web3 connection and accounts."""
    w3 = Web3(Web3.HTTPProvider("http://localhost:12537"))
    
    # cfxtest:aamr3rbhyjncc36v9rv3stc5csd2522kc2v4d1vp1u
    acct = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa")
    # cfxtest:aaru08p73np1gm9hbvm4gk8y8ue10m4pe62vc4ap4k
    acct2 = w3.account.from_key("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafb")
    
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


def cleanup_blockchain_data():
    """Remove blockchain_data folder if it exists."""
    blockchain_data_path = Path("../../EVoM-cfx-rust-oopsla24/dev-chain/blockchain_data")
    if blockchain_data_path.exists():
        print(f"Removing existing blockchain_data folder: {blockchain_data_path}")
        shutil.rmtree(blockchain_data_path)
        print("Blockchain data cleaned up successfully")
    else:
        print("No existing blockchain_data folder found")


def start_conflux_node():
    """Start the Conflux node."""
    dev_chain_path = Path("../../EVoM-cfx-rust-oopsla24/dev-chain")
    conflux_binary_path = Path("../../EVoM-cfx-rust-oopsla24/target/release/conflux")
    
    if not conflux_binary_path.exists():
        print(f"Error: Conflux binary not found at {conflux_binary_path}")
        print("Please build the project first with: cargo build --release")
        return None
    
    print(f"Starting Conflux node from {dev_chain_path}")
    print(f"Using binary: {conflux_binary_path}")
    
    # Start the conflux process
    process = subprocess.Popen(
        [str(conflux_binary_path), "--config", "development.toml"],
        cwd=dev_chain_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    return process


def wait_for_node_ready():
    """Wait for the Conflux node to be ready."""
    print("Waiting for Conflux node to be ready...")
    max_attempts = 60  # 5 minutes with 5-second intervals
    attempts = 0
    
    while attempts < max_attempts:
        try:
            response = requests.post(
                "http://localhost:12537",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "cfx_getStatus"
                },
                timeout=5
            )
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    print("Conflux node is ready!")
                    return True
        except Exception as e:
            pass
        
        print(f"Node not ready yet... (attempt {attempts + 1}/{max_attempts})")
        time.sleep(5)
        attempts += 1
    
    print("Error: Conflux node failed to start within timeout")
    return False


def copy_transaction_file(mode):
    """Copy the corresponding transaction file based on the experiment mode."""
    transaction_files = {
        "erc20": "../pregenerated_transaction_files_cfx/erc20_cfx_transactions_100k.txt",
        "native": "../pregenerated_transaction_files_cfx/native_cfx_transactions_100k.txt", 
        "cross-native": "../pregenerated_transaction_files_cfx/native_cfx_cross_transactions_100k.txt",
        "cross-erc20": "../pregenerated_transaction_files_cfx/erc20_cfx_cross_transactions_100k.txt"
    }
    
    source_file = Path(transaction_files.get(mode))
    target_file = Path("../../EVoM-cfx-rust-oopsla24/client/src/rpc/impls/transactions.txt")
    
    if not source_file.exists():
        print(f"Error: Transaction file not found: {source_file}")
        return False
    
    # Ensure the target directory exists
    target_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        print(f"Copying transaction file: {source_file} -> {target_file}")
        shutil.copy2(source_file, target_file)
        print("Transaction file copied successfully")
        return True
    except Exception as e:
        print(f"Error copying transaction file: {e}")
        return False


def run_setup_script(mode):
    """Run the appropriate setup script based on the experiment mode."""
    setup_scripts = {
        "erc20": "deploy_cfx_erc20.sh",
        "native": "deploy_cfx_native.sh", 
        "cross-native": "deploy_cfx_native_cross.sh",
        "cross-erc20": "deploy_cfx_cross_space_erc20.sh"
    }
    
    script_name = setup_scripts.get(mode, "deploy_cfx_cross_space_erc20.sh")
    setup_script_path = Path("../shell_deploy_scripts") / script_name
    
    if setup_script_path.exists():
        print(f"Running setup script for {mode} experiment: {setup_script_path}")
        try:
            result = subprocess.run(
                ["/bin/bash", script_name],
                cwd=Path("../shell_deploy_scripts"),
                timeout=300  # 5 minutes timeout
            )
            if result.returncode == 0:
                print("Setup script completed successfully")
                return True
            else:
                print(f"Setup script failed with return code {result.returncode}")
                return False
        except subprocess.TimeoutExpired:
            print("Setup script timed out")
            return False
        except Exception as e:
            print(f"Error running setup script: {e}")
            return False
    else:
        print(f"No setup script found for {mode} experiment at {setup_script_path}")
        print("Please create the appropriate setup script or use the default cross-space ERC20 script")
        return True


def trigger_benchmark():
    """Trigger the benchmark by sending request to the API."""
    print("Triggering benchmark...")
    try:
        requests.post(
            "http://localhost:12539",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "cfx_loadTest"
            },
            timeout=0.1  # Very short timeout, don't wait for response
        )
        return True
    except Exception as e:
        return True


def run_experiment(mode):
    """Run the experiment for the specified mode."""
    print(f"\n=== Starting {mode.upper()} Experiment ===")
    
    # Step 1: Clean up blockchain data
    cleanup_blockchain_data()
    
    # Step 2: Start Conflux node
    conflux_process = start_conflux_node()
    if conflux_process is None:
        return None
    
    try:
        # Step 3: Wait for node to be ready
        if not wait_for_node_ready():
            return None
        
        # Step 4: Run setup script
        if not run_setup_script(mode):
            return None
        
        # Step 5: Copy the corresponding transaction file
        if not copy_transaction_file(mode):
            return None
        
        # Step 6: Setup Web3 connection
        w3, acct, acct2 = setup_web3_and_accounts()
        
        # Step 7: Get transaction hashes for the mode
        hashes = get_transaction_hashes(mode)
        if not hashes:
            print(f"Error: Unknown mode '{mode}'")
            return None
        
        print(f"Using first hash: {hashes['first']}")
        print(f"Target hash: {hashes['last']}")
        
        # Step 8: Start a separate process to wait for the last transaction
        print("Starting separate process to wait for last transaction...")
        
        # Create a function to wait for the last transaction (will run in separate process)
        def wait_for_last_transaction_process(mode, last_hash):
            import time
            from conflux_web3 import Web3
            
            w3 = Web3(Web3.HTTPProvider("http://localhost:12537"))
            print(f"Process {os.getpid()}: Waiting for transaction {last_hash}")
            
            try:
                w3.cfx.wait_for_transaction_receipt(
                    transaction_hash=last_hash,
                    timeout=400,
                    poll_latency=0.05
                )
                print(f"Process {os.getpid()}: Last transaction processed successfully!")
                return True
            except Exception as e:
                print(f"Process {os.getpid()}: Error waiting for last transaction: {e}")
                return False
        
        # Start the waiting process
        import multiprocessing
        waiting_process = multiprocessing.Process(
            target=wait_for_last_transaction_process,
            args=(mode, hashes["last"])
        )
        waiting_process.start()
        
        # Wait a moment for the process to start
        time.sleep(0.5)
        
        # Step 9: Trigger the benchmark in the main process
        print("Triggering benchmark in main process...")
        benchmark_triggered = trigger_benchmark()
        t1_start = perf_counter()
        
        if not benchmark_triggered:
            print("Failed to trigger benchmark")
            waiting_process.terminate()
            return None
        
        # Step 10: Wait for the waiting process to complete
        print("Waiting for last transaction process to complete...")
        waiting_process.join(timeout=400)  # 400 second timeout
        
        t1_stop = perf_counter()
        
        if waiting_process.is_alive():
            print("Waiting process timed out, terminating...")
            waiting_process.terminate()
            waiting_process.join()
            return None
        
        if waiting_process.exitcode != 0:
            print("Waiting process failed")
            return None
        
        # Get transaction details
        try:
            tx_details = w3.cfx.get_transaction_by_hash(hashes['last'])
            print(f"Transaction details: {tx_details}")
        except Exception as e:
            print(f"Could not get transaction details: {e}")
        
        elapsed_time = t1_stop - t1_start
        print(f"Elapsed time for {mode} experiment: {elapsed_time:.4f} seconds")
        
        return elapsed_time
        
    finally:
        # Clean up the conflux process
        if conflux_process:
            print("Terminating Conflux node...")
            conflux_process.terminate()
            try:
                conflux_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("Force killing Conflux node...")
                conflux_process.kill()
                conflux_process.wait()


def main():
    parser = argparse.ArgumentParser(
        description="Run experiments on EVoM-cfx-rust-oopsla24",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python evom_cfx_rust_oopsla24_runner.py erc20
  python evom_cfx_rust_oopsla24_runner.py native
  python evom_cfx_rust_oopsla24_runner.py cross-native
  python evom_cfx_rust_oopsla24_runner.py cross-erc20
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
        # Change to the script directory
        script_dir = Path(__file__).parent
        os.chdir(script_dir)
        print(f"Changed working directory to: {script_dir}")
        
        # Run the experiment
        elapsed_time = run_experiment(args.mode)
        
        if elapsed_time is not None:
            print(f"\nExperiment completed successfully!")
            print(f"Total time taken: {elapsed_time:.4f} seconds")
        else:
            print("\nExperiment failed!")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\nExperiment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during experiment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 