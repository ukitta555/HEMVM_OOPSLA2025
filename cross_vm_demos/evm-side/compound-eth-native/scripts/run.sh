echo "-----------Step 1-------------"
npx hardhat run ./scripts/1_deploy.js --network localhost
echo "------------------------"
echo "-----------Step 2-------------"
npx hardhat run ./scripts/2_test.js --network localhost
echo "------------------------"
echo "-----------Step 3-------------"
npx hardhat run ./scripts/4_test.js --network localhost
echo "------------------------"