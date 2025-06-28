source ./cfx_addresses.sh

source ./activate_environment.sh

cd ../cfx_cross_chain/core_space

echo ">>> 0. Try compiling Solidity to short-circuit execution in case of a failure"
npx hardhat compile || exit 1;
echo "<<< Done."
echo "1. Deploy Core Space contracts and eSpace contracts, mint genesis tokens"

echo ">>> Deploy Core Space contracts & mint new ERC20 tokens."
npx hardhat run scripts/deployCoreSpaceAndMint.ts
echo "<<< Done."

echo ">>> Send money to eSpace."
npx hardhat run scripts/sendMoneyToESpace.ts
echo "<<< Done."

echo ">>> Check balance of mapped account."
npx hardhat run scripts/balanceMapped.ts
echo "<<< Done."

echo ">>> Deploy proxy to eSpace."
npx hardhat run scripts/deployESpaceContracts.ts
echo "<<< Done."


echo ">>> Get balance of CoreSpaceCoin."
npx hardhat run scripts/getBalanceERC20Core.ts
echo "<<< Done."

echo ">>> Create a vault and mirror contract for the CoreSpaceCoin."
npx hardhat run scripts/createVaultAndMirror.ts
echo "<<< Done."

echo ">>> Check CoreSpaceCoin balance in Core Space for main account."
npx hardhat run scripts/getBalanceERC20Core.ts
echo "<<< Done."

echo ">>> Check CoreSpaceCoin balance in eSpace for proxy."
cd ../espace
npx hardhat run scripts/getBalanceOfProxy_ERC20ESpace.ts
cd ../core_space
echo "<<< Done."


echo ">>> Deposit CoreSpaceCoin tokens cross-space."
npx hardhat run scripts/depositCrossSpace.ts
echo "<<< Done."


echo ">>> Check CoreSpaceCoin balance in Core Space for main account."
npx hardhat run scripts/getBalanceERC20Core.ts
echo "<<< Done."

echo ">>> Check CoreSpaceCoin balance in eSpace for proxy."
cd ../espace
npx hardhat run scripts/getBalanceOfProxy_ERC20ESpace.ts
cd ../core_space
echo "<<< Done."


echo ">>> Withdraw CoreSpaceCoin tokens cross-space."
npx hardhat run scripts/withdrawCrossSpace.ts
echo "<<< Done."


echo ">>> Check CoreSpaceCoin balance in Core Space for main account."
npx hardhat run scripts/getBalanceERC20Core.ts
echo "<<< Done."

echo ">>> Check CoreSpaceCoin balance in eSpace for proxy."
cd ../espace
npx hardhat run scripts/getBalanceOfProxy_ERC20ESpace.ts
cd ../core_space
echo "<<< Done."


echo ">>> Perform full-blown demo (20 tokens out, 10 tokens in)"
npx hardhat run scripts/demo.ts
echo "<<< Done."

echo ">>> Check CoreSpaceCoin balance in Core Space for main account."
npx hardhat run scripts/getBalanceERC20Core.ts
echo "<<< Done."

cd ../espace
echo ">>> Check CoreSpaceCoin balance in eSpace for proxy."
npx hardhat run scripts/getBalanceOfProxy_ERC20ESpace.ts
echo "<<< Done."

echo ">>> Check CoreSpaceCoin balance in eSpace for random address."
npx hardhat run scripts/getBalanceOfRandomAddress.ts
echo "<<< Done."
cd ../core_space

cd ../

echo "Script is finished!"