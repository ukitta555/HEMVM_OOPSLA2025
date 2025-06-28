source ./activate_environment.sh

source ./addresses.sh
cd ../



echo ">>> Request Aptos faucet for main account."
cd move-side/coin-move-compound
aptos account fund-with-faucet --account default --amount 99999999999$move_decimals
cd ../../
echo "<<< Done."

echo ">>> Deploy Move contracts."
cd move-side/coin-move-compound
aptos move publish --named-addresses coin_wrapper=default --assume-yes --max-gas 300000
cd ../../
echo "<<< Done."

echo ">>> Deploy EVM contracts."
cd evm-side/compound-eth-cross
npx hardhat run scripts/deploy_starter_eth.js --network localhost
cd ../..
echo "<<< Done."

echo ">>> Create mirror contracts on both sides"
echo "1. Init mirror Eth coin"
aptos move run --function-id $default::cross_vm_coin_compound::initialize_mirror_coin --type-args $default::mirror_coin::EthCoin --args hex:$eth_coin u8:8 --assume-yes --max-gas 300000
echo "2. Init mirror Diem coin"
aptos move run --function-id $default::cross_vm_coin_compound::initialize_vault_coin --type-args $default::native_coin::DiemCoin --assume-yes --max-gas 300000
echo "<<< Done."

echo ">>> Mint coin"
echo "1. Register Diem coin"
aptos move run --function-id 0x1::managed_coin::register --type-args $default::native_coin::DiemCoin --assume-yes
echo "2. Register mirror Eth coin"
aptos move run --function-id 0x1::managed_coin::register --type-args $default::mirror_coin::EthCoin --assume-yes
echo "3. Mint DMC(m)"
aptos move run --function-id $default::native_coin::mint --args address:$default u64:1000000$move_decimals --assume-yes
echo "4. Check DMC(m) balance"
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
cd ..
cd evm-side/compound-eth-cross
echo "5. Mint ETH(e)"
npx hardhat mint --account $eth_default --amount 1000000
echo "6. Check ETH(e) balance"
npx hardhat balance --token ETH --account $eth_default
cd ../..
echo "<<< Done. \n"

echo ">>> Deploy Compound to the ETH side"
cd evm-side/compound-eth-cross/scripts
./deploy_compound_to_eth_side.sh
cd ../../../
echo "<<< Done."

echo ">>> Deposit collateral to the Compound"
echo "1. Pre-execution balance."
cd move_scripts
echo "Balance of Diem Coin (Aptos side)"
python3 balance_of.py $default::native_coin::DiemCoin $default
echo "Balance of Eth Mirror Coin (Aptos side)"
python3 balance_of.py $default::mirror_coin::EthCoin $default
cd ../

cd evm-side/compound-eth-cross
echo "Balance of C_DiemMirrorCoin (Ethereum side)"
npx hardhat balance --token C_DMC --account 0x$cross_uniswap_proxy --network localhost
echo "Balance of ETHCoin (Ethereum side)"
npx hardhat balance --token ETH --account 0x$cross_uniswap_proxy --network localhost
echo "ETHCoin debt:"
npx hardhat get-debt --network localhost
cd ../../

echo "2. Deposit collateral & perform borrow."
aptos move run --function-id $default::cross_vm_coin_compound::deposit_collateral_and_borrow  --type-args $default::native_coin::DiemCoin $default::mirror_coin::EthCoin --args u64:5$move_decimals --assume-yes

echo "3. Post execution balance."
cd move_scripts
echo "Balance of Diem Coin (Aptos side)"
python3 balance_of.py $default::native_coin::DiemCoin $default
echo "Balance of Eth Mirror Coin (Aptos side)"
python3 balance_of.py $default::mirror_coin::EthCoin $default
cd ../

cd evm-side/compound-eth-cross
echo "Balance of C_DiemMirrorCoin (Ethereum side)"
npx hardhat balance --token C_DMC --account 0x$cross_uniswap_proxy --network localhost
echo "Balance of ETHCoin (Ethereum side)"
npx hardhat balance --token ETH --account 0x$cross_uniswap_proxy --network localhost
echo "ETHCoin debt:"
npx hardhat get-debt --network localhost
cd ../../


echo ">>> Repay debt and get back collateral"

echo "1. Repay debt & get back collateral ."
aptos move run --function-id $default::cross_vm_coin_compound::repay_debt_and_fetch_collateral  --type-args $default::native_coin::DiemCoin $default::mirror_coin::EthCoin --args u64:200000 --assume-yes

echo "2. Post execution balance."
cd move_scripts
echo "Balance of Diem Coin (Aptos side)"
python3 balance_of.py $default::native_coin::DiemCoin $default
echo "Balance of Eth Mirror Coin (Aptos side)"
python3 balance_of.py $default::mirror_coin::EthCoin $default
cd ../

cd evm-side/compound-eth-cross
echo "Balance of C_DiemMirrorCoin (Ethereum side)"
npx hardhat balance --token C_DMC --account 0x$cross_uniswap_proxy --network localhost
echo "Balance of ETHCoin (Ethereum side)"
npx hardhat balance --token ETH --account 0x$cross_uniswap_proxy --network localhost
echo "ETHCoin debt:"
npx hardhat get-debt --network localhost
cd ../../


echo "<<< Done."