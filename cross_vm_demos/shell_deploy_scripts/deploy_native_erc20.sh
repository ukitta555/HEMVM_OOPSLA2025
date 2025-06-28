source ./activate_environment.sh

cd ../evm-side/eth-erc-20/
echo "Deploy ERC-20 token..."
npx hardhat run scripts/deploy.ts
echo "ERC-20 deployed!"