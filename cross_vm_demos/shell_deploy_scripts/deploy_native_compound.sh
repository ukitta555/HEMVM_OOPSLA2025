source ./activate_environment.sh

echo "-----------Deploy Compound & Tokens & Mint genesis balance-------------"
cd ../evm-side/compound-eth-native
npx hardhat run ./scripts/1_deploy.js --network localhost
npx hardhat run ./scripts/2_test.js --network localhost
cd ../../shell_deploy_scripts
echo "------------------------"