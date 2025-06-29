# Artifact Overview

## 1. Introduction
This artifact accompanies the paper titled "HEMVM: a Heterogeneous Blockchain Framework for Interoperable Virtual Machines" and provides the source code along with a complete replication package. The purpose of this artifact is to facilitate the validation and reproduction of the research results presented in the paper. Users can explore the methodologies, execute the provided scripts, and verify the findings by using this carefully prepared package.

### Supported Claims

- **Claim 1:** Design that is presented in the paper (Figure 2, 4, 9, 12) is feasible. 

  *Supported by:* We provide the full source code of the prototype that compiles and runs.


- **Claim 2:** Empirical results presented in the paper (Table 1, 2) are reproducible.  

  *Supported by:* provided code artifact that can be used to evaluate the prototype to verify the stated claims.

---

## 2. Hardware Dependencies

The results presented in the paper have been obtained on a machine with 32GB RAM and a AMD Ryzen Threadripper PRO5945WX 12-Cores CPU.

We would recommend to use a 32GB machine for the evaluation of this artifact, although we believe it would still be possible to evaluate it even on a 16GB one, although it would be slower and the machine would sometimes hit its RAM capacity. 

There is no exact requirement on the CPU used to evaluate the artifact, but the speed of the processor will heavily influence the results of the benchmark and the compilation speed of large Rust codebases used in this artifact, therefore, a higher-end CPU would be preferred.

We highly recommend using a machine with an SSD to replicate the main results of the paper with at least 150GB of free storage to make sure that there is enough space for all compilation artifacts to be stored without affecting the performance of the machine.

There is no GPU requirements for this artifact.

## 3. Getting Started Guide

### Installation:

This artifact requires users install Docker first.

To install Docker please use one of the following resources:

1. [Install Docker for Ubuntu.](https://docs.docker.com/install/linux/docker-ce/ubuntu/)

2. [Install Docker for Mac.](https://docs.docker.com/docker-for-mac/install/)

3. [Install Docker for Windows.](https://docs.docker.com/docker-for-windows/install/)



After you have Docker installed, proceed to the DockerHub([link](https://hub.docker.com/repository/docker/ukitta555/oopsla2025hemvm/general)) and pull the image of the artifact:

```
sudo docker pull ukitta555/oopsla2025hemvm:latest
```

After you have pulled the image, execute the following command to start a temporary container using this image:

```
sudo docker run -it --rm ukitta555/oopsla2025hemvm:latest
```

To verify that the image is working correctly, you should perform the following steps:

1) Examine the folder structure. You should see 4 folders: "MoviEth", "EVoM-cfx-rust-oopsla24", "aptos-core", "cross_vm_demos". Considered in order, those folders represent 3 major blockchain clients that have been used to test the feasibility and performance of the framework, and "cross_vm_demos" is the folder with the smart contract code of the DeFi apps implemented on top of those clients. Alongside the smart contract code,  "cross_vm_demos" contains code that generates the workloads on which the framework was tested and the scripts that simplify the evaluation of the framework.
2) You should start your journey in "MoveXEther" folder. Use the following command to check whether a Rust binary for one of the clients has been generated when building the image:

```
cd EVoM-cfx-rust-oopsla24/target/release/ && ls -la
```

If you see a "conflux" binary, it means that one of the Rust compilation step has been successful, and we can at least partially start evaluating the artifact.

3) Now, go to the "cross_vm_demos" folder: 

```
cd ../../../cross_vm_demos && ls -la
```

There are three types of folders that are contained in "cross_vm_demos". Specifically, those are:

1) Folders with smart contract code (move-side, move-scripts, evm-side, cfx_cross_chain). These store code with DeFi apps built on top of our framework.

2) Folders with pregenerated experiment data (pregenerated_transaction_files_cfx, pregenerated_transactions_files, pregenerated_transactions_files_multiworker), which are there to save the evaluation comittee time in case they want to evaluate the artifact without generating data from scratch.

3) Infrastracture support (shell_deploy_scripts, uniswap_experiments, native_and_erc20_tokens_experiments, compound_experiments, experiment_runner). These folders contain code that helps to deploy smart contracts and DeFi protocols to the blockchain in order to set up the experiments, and also contain code that generates transaction workloads, which later go into folders from part 2).

We would like to point out the "experiment_runner" folder, which contains 4 runner scripts for different types of experiments that we have conducted, such as Conflux blockchain experiments, Aptos blockchain experiments, multi-threaded and single-threaded 500K txs HEMVM experiments (realistic workload), and 100K txs HEMVM experiments with maximal cache usage (maximum performance test workload). This folder will be the most useful for later evaluation.


## 4. Step-by-Step Instructions for Artifact Evaluation


### Reproducing Experiments
We assume that you always start from the "MoveXEther" folder.

1. **Experiment set 1: Conflux benchmarks (Table 1, last 2 rows)**
   - ``` cd cross_vm_demos/experiment_runner/ ```
   - Command to run: `python3 runner_cfx.py`, with possible arguments of ```native, erc20, cross-native, cross-erc20```
   - Full command would look like `python3 runner_cfx.py native` or `python3 runner_cfx.py cross-erc20` 
   - Expected runtime: 10-20 seconds on tested machine
   - Output location: terminal 
   - Output description: how many seconds it took to execute the payload of 100k transactions
   
2. **Experiment 2: Clean Aptos (Table 1, first 3 rows)**
   - ``` cd cross_vm_demos/experiment_runner/ ```
   - Command to run: `python3 runner_clean_aptos.py`
   - This will start compiling a clean Aptos blockchain client with no modification, and will run 3 different benchmarks on it
   - Output location: Terminal + File (`cd ./results && cat results_clean_aptos.txt`)
   - Output description: For each of the experiments, you will see a the number of seconds it took to finish the benchmark.


3. **Experiment 3: Single-threaded 100k transactions experiments (Table 1, everything else)**
   - ``` cd cross_vm_demos/experiment_runner/ ```
   - Command to run: `python3 runner.py`
   - This will start compiling a HEMVM version of Aptos client, and it will run the 100k transaction experiments from Table 1 in single-threaded mode.
   - Output location: Terminal + File (`cd ./results && cat results_prototype.txt`)
   - Output description: For each of the experiments, you will see a the number of seconds it took to finish the benchmark.


4. **Experiment 4: Multi-threaded and single-threaded 500k transactions experiments (Table 2)**
   - ``` cd cross_vm_demos/experiment_runner/ ```
   - Command to run: `python3 runner_multi_worker_prototype.py  --mode`, with a positional argument of `single-threaded` and `multithreaded`
   - Full command would look like `python3 runner_multi_worker_prototype.py  --mode multithreaded` 
   - This will start compiling a HEMVM version of Aptos client, and it will run the 500k transactions experiments from Table 2 in either multi-threaded or single-threaded mode, depending on the selected mode.
   - Output location: Terminal + File (`cd ./results && cat results.txt` or `cd ./results && cat results.txt`)
   - Output description: For each of the experiments, you will see a the number of seconds it took to finish the benchmark.

### Notes
- During execution, errors might pop up in the terminal - this is expected (e.g., some errors are due to off-by-one nonces that happen only once per workload, and some are just Rust errors when the client finish its work after handling the 100k transaction workload).
- How to interpret results: We expect the results to scale with the hardware, but the SSD and CPU will have the biggest impact. If the relative results stay the same (in terms of percentage gain/loss), we believe that the benchmark was reproduced.  

---

## 5. Reusability notes

### Adaptation Instructions
- Smaller/bigger experiment sizes: in case one would like to perform smaller/bigger experiments, they would need to go to folders that contain Python scripts that generate the transaction workloads (see section 3). 

To generate new transactions, you need to run a node in a background mode (`nohup cargo run --release -p aptos -- node run-local-testnet --with-faucet --faucet-port 8081 --force-restart --assume-yes --evm-genesis-account 0x14Dcb427A216216791fB63973c5b13878de30916 > ../logs.txt 2>&1 &`), then run the corresponding shell deploy script (in the `shell_deploy_scripts` folder), and the run the corresponding Python workload generation script. The correspondance can be inferred from the runner files described in section 4.
 

## CONTACT
Vladyslav Nekriach (vladyslav.nekriach@gmail.com)

## Acknowledgement
This research has received support from the National Key Research and Development Project of China (Grant Nos. 2023YFB2704900 and 2022YFB2702300).

---