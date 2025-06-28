from funding_utils import FundingType, fund_wallets
import asyncio
import os.path
import shutil
import time
from pprint import pprint
from subprocess import Popen, PIPE
from pathlib import Path
import requests
import argparse

# Import the prototype setup utility
from prototype_setup import get_movieth_folder

RUNS = 1


class Experiment:
    file_path_with_required_txs: Path
    deployment_script: Path
    funding_type: FundingType
    only_eth_coin_deployed: bool
    erc_20_cross_setup: bool

    def __init__(
        self, 
        file_path_with_required_txs, 
        deployment_script,
        funding_type,
        only_eth_coin_deployed,
        erc_20_cross_setup
    ):
        self.file_path_with_required_txs = file_path_with_required_txs
        self.deployment_script = deployment_script
        self.funding_type = funding_type
        self.only_eth_coin_deployed = only_eth_coin_deployed
        self.erc_20_cross_setup = erc_20_cross_setup
    
    def __str__(self):
        return f"Experiment supporting data - path to transactions: {self.file_path_with_required_txs}, path to deployment script: {self.deployment_script}"


# CARGO_PATH = "/home/fanlgrp/.cargo/bin/cargo"
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



def write_to_file(final_results, experiments, execution_mode):
    filename = f"./results/results_{execution_mode}.txt"
    with open(filename, 'w') as f:
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


# Full deployment:
# Proxy (which is also ERC20) = 0xcC166f312524Cc88E2c16c3bdd5735a23376B1fb
# Coin = 0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc
# Only coin deployed:
# Coin = 0xcC166f312524Cc88E2c16c3bdd5735a23376B1fb
async def run_experiments(experiments: dict[str, Experiment], execution_mode: str):
    results = dict()
    
    # Select the appropriate endpoint based on execution mode
    if execution_mode == "multithreaded":
        benchmark_url = "http://0.0.0.0:8080/v1/stress_test_move"
    elif execution_mode == "single-threaded":
        benchmark_url = "http://0.0.0.0:8080/v1/stress_test_move_single_thread_ignore_types"
    else:
        raise ValueError(f"Invalid execution mode: {execution_mode}")
    
    for experiment in experiments.keys():
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
             

                file_path_with_required_txs = experiments[experiment].file_path_with_required_txs
                deployment_script = experiments[experiment].deployment_script

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
                
                await fund_wallets(experiment=experiments[experiment])

                # run "cp *file_path_with_required_txs*  *path where the benchmarking endpoint expects it to be*"
                print(f"Copy transactions with path {file_path_with_required_txs} to the prototype folder")
                shutil.copy(file_path_with_required_txs, prototype_folder/"api/src/move_transactions.txt")
                print("Copy successful!")

                # ping the endpoint to run the experiment 
                print(f"Starting benchmark with {execution_mode} mode...")
                try:
                    requests.post(
                        url=benchmark_url,
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
    final_results = fetch_data_from_stringified_results(results, experiments.keys())
    pprint(final_results)
    write_to_file(final_results, experiments.keys(), execution_mode)
            

if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Run experiments with different execution modes')
    parser.add_argument(
        '--mode', 
        choices=['multithreaded', 'single-threaded'], 
        required=True,
        help='Execution mode: multithreaded or single-threaded'
    )
    
    args = parser.parse_args()
    execution_mode = args.mode
    
    print(f"Running experiments in {execution_mode} mode")
    
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    print("Changed current dir to ", os.path.dirname(os.path.realpath(__file__)))
    dir_with_pregenerated_txs = Path(os.getcwd()).parent / 'pregenerated_transactions_files_multiworker'
    dir_with_deploy_scripts = Path(os.getcwd()).parent / 'shell_deploy_scripts'

    experiments = {
        # "move_native_token_intra": Experiment(
        #     file_path_with_required_txs=dir_with_pregenerated_txs/"move_native_token_intra_500k.txt", 
        #     deployment_script=dir_with_deploy_scripts/"deploy_aptos_accounts.sh",
        #     funding_type=FundingType.NATIVE_APTOS,
        #     only_eth_coin_deployed=False,
        #     erc_20_cross_setup=False
        # ), # OK
        # "move_coin_intra": Experiment(
        #     file_path_with_required_txs=dir_with_pregenerated_txs/"move_custom_token_intra_500k.txt", 
        #     deployment_script=dir_with_deploy_scripts/"deploy_aptos_coin.sh",
        #     funding_type=FundingType.NATIVE_AND_CUSTOM_APTOS,
        #     only_eth_coin_deployed=False,
        #     erc_20_cross_setup=False
        # ), # OK
        # "eth_native_token_intra": Experiment(
        #     file_path_with_required_txs=dir_with_pregenerated_txs/"eth_native_token_intra_multiworker_500k.txt", 
        #     deployment_script=dir_with_deploy_scripts/"deploy_aptos_accounts.sh",
        #     funding_type=FundingType.NATIVE_ETH,
        #     only_eth_coin_deployed=False,
        #     erc_20_cross_setup=False
        # ), # OK
        # "eth_erc20_intra": Experiment(
        #     dir_with_pregenerated_txs/"eth_custom_token_intra_multiworker_500k.txt", 
        #     dir_with_deploy_scripts/"deploy_native_erc20.sh",
        #     funding_type=FundingType.NATIVE_AND_CUSTOM_ETH,
        #     only_eth_coin_deployed=True,
        #     erc_20_cross_setup=False
        # ), # OK
        # "move_native_token_cross": Experiment(
        #     file_path_with_required_txs=dir_with_pregenerated_txs/"move_native_token_cross_multiworker_500k_cpy.txt", 
        #     deployment_script=dir_with_deploy_scripts/"deploy_cross_space_erc20_and_native_coin.sh",
        #     funding_type=FundingType.NATIVE_APTOS,
        #     only_eth_coin_deployed=False,
        #     erc_20_cross_setup=False
        # ), # OK
        # "move_coin_cross": Experiment(
        #     dir_with_pregenerated_txs/"move_custom_token_cross_multiworker_500k.txt", 
        #     dir_with_deploy_scripts/"deploy_cross_space_erc20_and_native_coin.sh",
        #     funding_type=FundingType.NATIVE_AND_CUSTOM_APTOS,
        #     only_eth_coin_deployed=False,
        #     erc_20_cross_setup=False
        # ), # OK
        # "eth_native_token_cross": Experiment(
        #     file_path_with_required_txs=dir_with_pregenerated_txs/"eth_native_token_cross_multiworker_500k.txt", 
        #     deployment_script=dir_with_deploy_scripts/"deploy_cross_space_erc20_and_native_coin.sh",
        #     funding_type=FundingType.NATIVE_ETH,
        #     only_eth_coin_deployed=False,
        #     erc_20_cross_setup=False
        # ), # OK
        # "eth_erc20_cross": Experiment(
        #     file_path_with_required_txs=dir_with_pregenerated_txs/"eth_custom_token_cross_multiworker_500k.txt", 
        #     deployment_script=dir_with_deploy_scripts/"deploy_cross_space_erc20_and_native_coin.sh",
        #     funding_type=FundingType.NATIVE_AND_CUSTOM_BOTH,
        #     only_eth_coin_deployed=False,
        #     erc_20_cross_setup=True
        # ), # OK
        # "intra_uniswap": Experiment(
        #     file_path_with_required_txs=dir_with_pregenerated_txs/"uniswap_intra_multiworker_500k.txt",
        #     deployment_script=dir_with_deploy_scripts/"deploy_cross_uniswap.sh",
        #     funding_type=FundingType.UNISWAP_EXPERIMENT,
        #     only_eth_coin_deployed=False,
        #     erc_20_cross_setup=True
        # ), # OK
        # "cross_uniswap": Experiment(
        #     file_path_with_required_txs=dir_with_pregenerated_txs/"uniswap_cross_multiworker_500k.txt",
        #     deployment_script=dir_with_deploy_scripts/"deploy_cross_uniswap.sh",
        #     funding_type=FundingType.UNISWAP_CROSS_EXPERIMENT,
        #     only_eth_coin_deployed=False,
        #     erc_20_cross_setup=True
        # ),
        # "intra_pancakeswap": Experiment(
        #     file_path_with_required_txs=dir_with_pregenerated_txs/"pancakeswap_intra_multiworker_500k.txt",
        #     deployment_script=dir_with_deploy_scripts/"deploy_cross_pancake_swap.sh", # use cross deploy script to save time writing additional code
        #     funding_type=FundingType.PANCAKE_EXPERIMENT,
        #     only_eth_coin_deployed=False,
        #     erc_20_cross_setup=True
        # ),
        # "cross_pancakeswap": Experiment(
        #     file_path_with_required_txs=dir_with_pregenerated_txs/"pancakeswap_cross_multiworker_500k.txt",
        #     deployment_script=dir_with_deploy_scripts/"deploy_cross_pancake_swap.sh", # use cross deploy script to save time writing additional code
        #     funding_type=FundingType.PANCAKE_CROSS_EXPERIMENT,
        #     only_eth_coin_deployed=False,
        #     erc_20_cross_setup=True
        # ),
        # # SALAD EXPERIMENTS
        "salad_uniswap_pancake_uni45_pancake45_cross10": Experiment(
            file_path_with_required_txs=dir_with_pregenerated_txs/"salad_uniswap_pancake_uni45_pancake45_cross10_500k.txt",
            deployment_script=dir_with_deploy_scripts/"deploy_cross_pancake_and_uniswap.sh", # use cross deploy script to save time writing additional code
            funding_type=FundingType.MIX_UNI_PANCAKE_CROSS_EXPERIMENT,
            only_eth_coin_deployed=False,
            erc_20_cross_setup=True
        ),
        "salad_80_20_native_coin": Experiment(
            file_path_with_required_txs=dir_with_pregenerated_txs/"salad_native_coin_e80_m20_500k.txt", 
            deployment_script=dir_with_deploy_scripts/"deploy_cross_space_erc20_and_native_coin.sh",
            funding_type=FundingType.NATIVE_BOTH,
            only_eth_coin_deployed=False,
            erc_20_cross_setup=False
        ), # OK
        "salad_70_20_10_native_coin": Experiment(
            file_path_with_required_txs=dir_with_pregenerated_txs/"salad_native_coin_e70_m20_ec5_mc5_multiorigin_500k.txt",
            deployment_script=dir_with_deploy_scripts/"deploy_cross_space_erc20_and_native_coin.sh",
            funding_type=FundingType.NATIVE_BOTH,
            only_eth_coin_deployed=False,
            erc_20_cross_setup=False
        ), # OK
        "salad_60_40_ERC20_custom_coin_500k": Experiment(
            file_path_with_required_txs=dir_with_pregenerated_txs/"salad_ERC_custom_coin_e60_m40_500k.txt", 
            deployment_script=dir_with_deploy_scripts/"deploy_cross_space_erc20_and_native_coin.sh",
            funding_type=FundingType.NATIVE_AND_CUSTOM_BOTH,
            only_eth_coin_deployed=False,
            erc_20_cross_setup=False
        ), # OK
        "salad_55_35_10_ERC20_custom_coin_500k": Experiment(
            file_path_with_required_txs=dir_with_pregenerated_txs/"salad_ERC_custom_coin_e55_m35_c10_500k.txt", 
            deployment_script=dir_with_deploy_scripts/"deploy_cross_space_erc20_and_native_coin.sh",
            funding_type=FundingType.NATIVE_AND_CUSTOM_BOTH,
            only_eth_coin_deployed=False,
            erc_20_cross_setup=True
        ), # OK
        "salad_pancake_custom15_pancake15_erc70": Experiment(
            file_path_with_required_txs=dir_with_pregenerated_txs/"salad_pancake_custom15_pancake15_erc70_500k.txt",
            deployment_script=dir_with_deploy_scripts/"deploy_cross_pancake_and_uniswap.sh", # use cross deploy script to save time writing additional code
            funding_type=FundingType.MIX_PANCAKE_EXPERIMENT_NATIVE_ONLY,
            only_eth_coin_deployed=False,
            erc_20_cross_setup=True
        ),
        "salad_pancake_custom15_pancake15_erc60_crosspan10": Experiment(
            file_path_with_required_txs=dir_with_pregenerated_txs/"salad_pancake_custom15_pancake15_erc60_crosspan10_500k.txt",
            deployment_script=dir_with_deploy_scripts/"deploy_cross_pancake_and_uniswap.sh ", # use cross deploy script to save time writing additional code
            funding_type=FundingType.MIX_PANCAKE_EXPERIMENT_NATIVE_AND_CROSS,
            only_eth_coin_deployed=False,
            erc_20_cross_setup=True
        ),
        "salad_uniswap_intra20_erc30_custom50": Experiment(
            file_path_with_required_txs=dir_with_pregenerated_txs/"salad_uniswap_intra20_erc30_custom50_500k.txt",
            deployment_script=dir_with_deploy_scripts/"deploy_cross_uniswap.sh", # use cross deploy script to save time writing additional code
            funding_type=FundingType.MIX_UNISWAP_EXPERIMENT,
            only_eth_coin_deployed=False,
            erc_20_cross_setup=True
        ),
        "salad_uniswap_intra20_cross10_erc30_custom40": Experiment(
            file_path_with_required_txs=dir_with_pregenerated_txs/"salad_uniswap_intra20_cross10_erc30_custom40_500k.txt",
            deployment_script=dir_with_deploy_scripts/"deploy_cross_uniswap.sh", # use cross deploy script to save time writing additional code
            funding_type=FundingType.MIX_UNISWAP_EXPERIMENT,
            only_eth_coin_deployed=False,
            erc_20_cross_setup=True
        ),
        "salad_uniswap_pancake_uni45_pancake55": Experiment(
            file_path_with_required_txs=dir_with_pregenerated_txs/"salad_uniswap_pancake_uni45_pancake55_500k.txt",
            deployment_script=dir_with_deploy_scripts/"deploy_cross_pancake_and_uniswap.sh", # use cross deploy script to save time writing additional code
            funding_type=FundingType.MIX_UNI_PANCAKE_NATIVE_EXPERIMENT,
            only_eth_coin_deployed=False,
            erc_20_cross_setup=True
        ),
    }

    # TODO: parametrize experiments according to whether we need to fund NPC accounts or not
    asyncio.run(run_experiments(experiments, execution_mode))


