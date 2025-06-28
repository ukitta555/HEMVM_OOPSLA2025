source ./activate_environment.sh
cd ../evm-side/uniswap-eth-native
echo "Deploy Native Uniswap..."
npx hardhat run deploy_eth_uniswap.ts