echo "-----------Step 1-------------"
npx hardhat run ./1_deploy.js --network localhost
echo "------------------------"
echo "-----------Step 2-------------"
npx hardhat run ./2_test.js --network localhost
echo "------------------------"