#!/usr/bin/env python3

# Copyright © Aptos Foundation
# SPDX-License-Identifier: Apache-2.0

"""
10**6 / 2578
387.8975950349108 - naive Python benchmark for ETH only transfers
"""


# Accumulative TPS: 9117 - concurrency 1 (ETH) -> flawed experiment?
# Accumulative TPS ~ 3800 - concurrency 1 (Aptos)

# don't measure in concurrent mode!
# ask Peilun whether we are writing everything to the disk
# increase block size, concurrency = 1

import re
import os
import tempfile
import json
from typing import Callable, Optional, Tuple, Mapping, Sequence, Any
from tabulate import tabulate
from subprocess import Popen, PIPE, CalledProcessError
from dataclasses import dataclass


# numbers are based on the machine spec used by github action
# Local machine numbers will be higher.
EXPECTED_TPS = {
    # ("no-op", False, 1): (18800.0, True),
    # ("no-op", False, 1000): (2980.0, True),
    # ("coin-transfer", False, 1): (12600.0, True),
    ("coin-transfer", True, 1): (22100.0, True),
    # ("account-generation", False, 1): (11000.0, True),
    # ("account-generation", True, 1): (17600.0, True),
    # changed to not use account_pool. either recalibrate or add here to use account pool.
    # ("account-resource32-b", False, 1): (13000.0, False),
    # ("modify-global-resource", False, 1): (3700.0, True),
    # ("modify-global-resource", False, 10): (10800.0, True),
    # # seems to have changed, disabling as land_blocking, until recalibrated
    # ("publish-package", False, 1): (159.0, False),
    # ("batch100-transfer", False, 1): (350, True),
    # ("batch100-transfer", True, 1): (553, True),
    # ("token-v1ft-mint-and-transfer", False, 1): (1650.0, True),
    # ("token-v1ft-mint-and-transfer", False, 20): (7100.0, True),
    # ("token-v1nft-mint-and-transfer-sequential", False, 1): (1100.0, True),
    # ("token-v1nft-mint-and-transfer-sequential", False, 20): (5350.0, True),
    # ("token-v1nft-mint-and-transfer-parallel", False, 1): (1380.0, True),
    # ("token-v1nft-mint-and-transfer-parallel", False, 20): (5450.0, True),
    # # ("token-v1ft-mint-and-store", False): 1000.0,
    # # ("token-v1nft-mint-and-store-sequential", False): 1000.0,
    # # ("token-v1nft-mint-and-store-parallel", False): 1000.0,
    # ("no-op2-signers", False, 1): (18800.0, True),
    # ("no-op5-signers", False, 1): (18800.0, True),
    # ("token-v2-ambassador-mint", False, 1): (1750.0, True),
    # ("token-v2-ambassador-mint", False, 20): (5500.0, True),
}

NOISE_LOWER_LIMIT = 0.8
NOISE_LOWER_LIMIT_WARN = 0.9
# If you want to calibrate the upper limit for perf improvement, you can
# increase this value temporarily (i.e. to 1.3) and readjust back after a day or two of runs
NOISE_UPPER_LIMIT = 1.15
NOISE_UPPER_LIMIT_WARN = 1.05

# bump after a perf improvement, so you can easily distinguish runs
# that are on top of this commit
CODE_PERF_VERSION = "v3"

# use production concurrency level for assertions
CONCURRENCY_LEVEL = 1
BLOCK_SIZE = 10000
NUM_BLOCKS = 15
NUM_BLOCKS_DETAILED = 10
NUM_ACCOUNTS = max([2000000, 4 * NUM_BLOCKS * BLOCK_SIZE])
ADDITIONAL_DST_POOL_ACCOUNTS = 2 * NUM_BLOCKS * BLOCK_SIZE
MAIN_SIGNER_ACCOUNTS = 2 * BLOCK_SIZE

if os.environ.get("DETAILED"):
    EXECUTION_ONLY_CONCURRENCY_LEVELS = [1, 2, 4, 8, 16, 32, 60]
else:
    EXECUTION_ONLY_CONCURRENCY_LEVELS = []

if os.environ.get("RELEASE_BUILD"):
    BUILD_FLAG = "--release"
else:
    BUILD_FLAG = "--profile performance"
    # BUILD_FLAG = ""

# Run the single node with performance optimizations enabled
target_directory = "execution/executor-benchmark/src"

print(f"Build flag: {BUILD_FLAG}")
print(f"Concurrency level: {CONCURRENCY_LEVEL}")

def execute_command(command):
    result = []
    with Popen(
            command,
            shell=True,
            text=True,
            cwd=target_directory,
            stdout=PIPE,
            bufsize=1,
            universal_newlines=True,
    ) as p:
        # stream to output while command is executing
        if p.stdout is not None:
            for line in p.stdout:
                print(line, end="")
                result.append(line)

    if p.returncode != 0:
        raise CalledProcessError(p.returncode, p.args)

    # return the full output in the end for postprocessing
    full_result = "\n".join(result)

    if " ERROR " in full_result:
        print("ERROR log line in execution")
        exit(1)

    return full_result

errors = []
warnings = []

with tempfile.TemporaryDirectory() as tmpdirname:
    create_db_command = f"cargo run {BUILD_FLAG} -- --block-size {BLOCK_SIZE} --concurrency-level {CONCURRENCY_LEVEL}  create-db --data-dir {tmpdirname}/db --num-accounts {NUM_ACCOUNTS}"
    output = execute_command(create_db_command)
    results = []

    for (transaction_type, use_native_executor, module_working_set_size), (
            expected_tps,
            check_active,
    ) in EXPECTED_TPS.items():
        print(f"Testing {transaction_type}")

        cur_block_size = int(min([expected_tps, BLOCK_SIZE]))
        print(f"Current block size: {cur_block_size}")

        common_command_suffix = f"--block-size {cur_block_size} run-executor --data-dir {tmpdirname}/db  --checkpoint-dir {tmpdirname}/cp"

        concurrency_level_results = {}

        test_db_command = f"cargo run {BUILD_FLAG} -- --concurrency-level {CONCURRENCY_LEVEL} {common_command_suffix} --blocks {NUM_BLOCKS}"
        print(test_db_command)
        output = execute_command(test_db_command)


if warnings:
    print("Warnings: ")
    print("\n".join(warnings))

if errors:
    print("Errors: ")
    print("\n".join(errors))
    exit(1)

exit(0)