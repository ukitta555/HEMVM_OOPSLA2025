import enum
import os.path
import shutil
import time
from pprint import pprint
from subprocess import Popen, PIPE
from pathlib import Path
import requests

# Import the prototype setup utility
from prototype_setup import get_movieth_folder

RUNS = 1

class TransactionsSubspace(enum.Enum):
    MOVE = 0
    ETHEREUM = 1

os.chdir(os.path.dirname(os.path.realpath(__file__)))
print("Changed current dir to ", os.path.dirname(os.path.realpath(__file__)))
dir_with_pregenerated_txs = Path(os.getcwd()).parent / 'pregenerated_transactions_files'
dir_with_deploy_scripts = Path(os.getcwd()).parent / 'shell_deploy_scripts'

file_paths_with_pregenerated_txs = {
    "pancake_cross": (dir_with_pregenerated_txs/"pancake_cross_100k.txt", TransactionsSubspace.ETHEREUM, dir_with_deploy_scripts/"deploy_cross_pancake_swap.sh"),
    "pancake_intra": (dir_with_pregenerated_txs/"pancake_intra_100k.txt", TransactionsSubspace.MOVE, dir_with_deploy_scripts/"deploy_native_pancake_swap.sh"),
    "uniswap_intra": (dir_with_pregenerated_txs/"uniswap_intra_100k.txt", TransactionsSubspace.ETHEREUM, dir_with_deploy_scripts/"deploy_native_uniswap.sh"),
    "uniswap_cross": (dir_with_pregenerated_txs/"uniswap_cross_100k.txt", TransactionsSubspace.MOVE, dir_with_deploy_scripts/"deploy_cross_uniswap.sh"),
    "compound_intra": (dir_with_pregenerated_txs/"compound_intra_100k.txt", TransactionsSubspace.ETHEREUM, dir_with_deploy_scripts/"deploy_native_compound.sh"),
    "compound_cross": (dir_with_pregenerated_txs/"compound_cross_100k.txt", TransactionsSubspace.MOVE, dir_with_deploy_scripts/"deploy_cross_compound.sh"),
    "move_native_token_intra": (dir_with_pregenerated_txs/"move_native_token_intra_100k.txt", TransactionsSubspace.MOVE, dir_with_deploy_scripts/"deploy_aptos_accounts.sh"),
    "move_coin_intra": (dir_with_pregenerated_txs/"move_coin_intra_100k.txt", TransactionsSubspace.MOVE, dir_with_deploy_scripts/"deploy_aptos_coin.sh"),
    "eth_native_token_intra": (dir_with_pregenerated_txs/"eth_native_token_intra_100k.txt", TransactionsSubspace.ETHEREUM, dir_with_deploy_scripts/"deploy_aptos_accounts.sh"), # could place None but need to handle it explicitly
    "eth_erc20_intra": (dir_with_pregenerated_txs/"eth_coin_intra_100k.txt", TransactionsSubspace.ETHEREUM, dir_with_deploy_scripts/"deploy_native_erc20.sh"),
    "move_native_token_cross": (dir_with_pregenerated_txs/"move_native_token_cross_100k.txt", TransactionsSubspace.MOVE, dir_with_deploy_scripts/"deploy_cross_space_erc20_and_native_coin.sh"),
    "move_coin_cross": (dir_with_pregenerated_txs/"move_coin_cross_100k.txt", TransactionsSubspace.MOVE, dir_with_deploy_scripts/"deploy_cross_space_erc20_and_native_coin.sh"),
    "eth_native_token_cross": (dir_with_pregenerated_txs/"eth_native_token_cross_100k.txt", TransactionsSubspace.ETHEREUM, dir_with_deploy_scripts/"deploy_cross_space_erc20_and_native_coin.sh"),
    "eth_erc20_cross": (dir_with_pregenerated_txs/"eth_coin_cross_100k.txt", TransactionsSubspace.ETHEREUM, dir_with_deploy_scripts/"deploy_cross_space_erc20_and_native_coin.sh")
}

CARGO_PATH = "cargo"
aptos_binary_execution_command = \
    f"{CARGO_PATH} run --release -p aptos -- node run-local-testnet --with-faucet --faucet-port 8081 --force-restart --assume-yes --evm-genesis-account 0x14Dcb427A216216791fB63973c5b13878de30916"

# Use the prototype setup utility to get the MoviEth folder dynamically
prototype_folder = get_movieth_folder()


def poll_faucet_until_ready():
    faucet_url = "http://localhost:8081/mint?amount=10000&address=0x1"
    while True:
        response = None
        try:
            response = requests.post(
                faucet_url,
                data={}
            )
        except Exception as e:
            pass
        if not response or response.status_code >= 300:
            print("Faucet is still asleep..")
        elif response.status_code == 200:
            print("Faucet is alive!")
            break
        time.sleep(2)


def write_to_file(final_results, experiments):
    with open("./results/results_prototype.txt", 'w') as f:
        for experiment in experiments:
            f.write(str(experiment) + "\n")
            f.write("-------------\n")
            f.write("[")
            for index, time in enumerate(final_results[experiment]):     
                f.write(str(time))
                if index < len(final_results[experiment]) - 1:
                    f.write(",")
            f.write("]" + "\n")
            f.write("-------------\n")


def fetch_data_from_stringified_results(results, experiments):
    final_results = dict()
    for experiment in experiments:
        experiment_results = results[experiment]
        final_results[experiment] = [float(stringified_time[13:-1]) for stringified_time in experiment_results]
    return final_results

def run_experiments():
    results = dict()
    experiments = file_paths_with_pregenerated_txs.keys()
    for experiment in experiments:
        for run_index in range(0, RUNS):
            print(experiment, run_index)
            with Popen(
                args=aptos_binary_execution_command,
                shell=True,
                stdout=PIPE,
                text=True,
                bufsize=1,
                cwd=prototype_folder,
            ) as aptos_process:
                print("Launched aptos binary!")
                print("Start polling faucet...")
                poll_faucet_until_ready()

                file_path_with_required_txs, transactions_subspace, deployment_script = file_paths_with_pregenerated_txs[experiment]
               
                # run deployment of the protocols required for the current experiment
                print(f"Launched deploy script for {experiment}...")
                with Popen(
                    f"/bin/bash {deployment_script}",
                    cwd=dir_with_deploy_scripts,
                    shell=True,
                    stdout=PIPE,
                ) as deploy_script:    
                    if deploy_script.stdout is not None:
                        for line in deploy_script.stdout:
                            print(line.decode("utf-8"), end="")
                    deploy_script.wait() # just to be 100% sure

                # run "cp *file_path_with_required_txs*  *path where the benchmarking endpoint expects it to be*"
                if transactions_subspace == TransactionsSubspace.ETHEREUM:
                    print(f"Copy transactions with path {file_path_with_required_txs} to Ethereum side")
                    shutil.copy(file_path_with_required_txs, prototype_folder/"api/ethrpc/src/impls/transactions.txt")
                else:
                    print(f"Copy transactions with path {file_path_with_required_txs} to Move side")
                    shutil.copy(file_path_with_required_txs, prototype_folder/"api/src/move_transactions.txt")

                # ping the correct endpoint to run the experiment
                if transactions_subspace == TransactionsSubspace.ETHEREUM:
                    print("Starting benchmark on Ethereum side...")
                    try:
                        requests.post(
                            url="http://localhost:8545/",
                            json={
                                "jsonrpc": "2.0",
                                "id": 2,
                                "method": "eth_stressTestUniswap"
                            },
                            timeout=1
                        )
                    except Exception as e:
                        pass 
                else:
                    print("Starting benchmark on Move side...")
                    try:
                        requests.post(
                            url="http://0.0.0.0:8080/v1/stress_test_move_single_thread",
                            json={},
                            timeout=1
                        )
                    except Exception as e:
                        pass
                # collect output data / search for the line with the runtime of the experiment
                if aptos_process.stdout is not None:
                    for line in aptos_process.stdout:
                        print(line, end="")
                        if "report time: " in line:
                            # print(line, end="")
                            if not results.get(experiment): 
                                results[experiment] = [line]
                            else: 
                                results[experiment].append(line)
            print("Aptos binary terminated! Sleeping for a moment to check whether the result was captured..")
            print(results[experiment])
            time.sleep(3)
    final_results = fetch_data_from_stringified_results(results, experiments)
    pprint(final_results)
    write_to_file(final_results, experiments)
            

if __name__ == "__main__":
    run_experiments()