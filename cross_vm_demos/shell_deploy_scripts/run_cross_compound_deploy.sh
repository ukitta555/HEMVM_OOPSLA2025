clear

cd ../move-side/coin-move-compound
aptos move compile --named-addresses coin_wrapper=default || exit 1;
cd ../../shell_deploy_scripts/

cd ../evm-side/compound-eth-cross/
npx hardhat compile || exit 1;
cd ../../shell_deploy_scripts/
./deploy_cross_compound.sh