#!/bin/bash

# CFX ERC20 Experiment Setup Script
# This script sets up the environment for ERC20 token experiments on Conflux

set -e

echo "=== Setting up CFX ERC20 Experiment ==="
cd ../native_and_erc20_tokens_experiments/conflux_experiments/scripts
npx hardhat run deploy.ts
cd ../../..

echo "<<< Done."