source ./activate_environment.sh

source ./addresses.sh
cd ../



echo ">>> Deploy Move contract."
cd move-side/just-coin-cross
echo "1. Request faucet"
aptos account fund-with-faucet --account default --amount 999999999999
aptos account fund-with-faucet --account default2 --amount 999999999999
echo "2. Deploy contract"
aptos move publish --named-addresses coin_wrapper=default --assume-yes --max-gas 300000
cd ../..
echo "<<< Done. \n"

echo ">>> Deploy EVM contract."
cd evm-side/cross-erc-20
npx hardhat run scripts/deploy.ts --network localhost
cd ../..
echo "<<< Done. \n"

echo ">>> Initialize coin"
cd move_scripts
echo "1. Init mirror Eth coin"
aptos move run --function-id $default::cross_vm_coin_erc20::initialize_mirror_coin --type-args $default::mirror_coin::EthCoin --args hex:$eth_coin u8:8 --assume-yes --max-gas 300000
echo "2. Init Diem coin"
aptos move run --function-id $default::cross_vm_coin_erc20::initialize_vault_coin --type-args $default::native_coin::DiemCoin --assume-yes --max-gas 300000
cd ..
echo "<<< Done. \n"


echo ">>> Mint coin"
echo "1. Register Diem coin"
aptos move run --function-id 0x1::managed_coin::register --type-args $default::native_coin::DiemCoin --assume-yes
aptos move run --function-id 0x1::managed_coin::register --type-args $default::native_coin::DiemCoin --assume-yes --profile default2
echo "2. Register mirror Eth coin"
aptos move run --function-id 0x1::managed_coin::register --type-args $default::mirror_coin::EthCoin --assume-yes
echo "3. Mint DMC(m)"
aptos move run --function-id $default::native_coin::mint --args address:$default u64:1000000000$move_decimals --assume-yes
echo "4. Check DMC(m) balance"
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
cd ..
cd evm-side/cross-erc-20
echo "5. Mint ETH(e)"
npx hardhat mint --account $eth_default --amount 100000000000
echo "6. Check ETH(e) balance"
npx hardhat balance --token ETH --account $eth_default
cd ../..
echo "<<< Done. \n"

echo ">>> Transfer ETH from Ethereum to Move"
echo "1. Transfer from Ethereum"
cd evm-side/cross-erc-20
npx hardhat cross-transfer --token ETH --receiver $default --amount 170000
echo "2. Check Sender Balance"
npx hardhat balance --token ETH --account $eth_default
cd ../..
echo "3. Check Receiver Balance"
cd move_scripts
python3 balance_of.py $default::mirror_coin::EthCoin $default
cd ..
echo "<<< Done. \n"


echo ">>> Transfer DMC from Move to Ethereum"
echo "1. Transfer from Move"
aptos move run --function-id $default::cross_vm_coin_erc20::deposit --type-args $default::native_coin::DiemCoin --args hex:${eth_default:2:40} u64:190000$move_decimals --assume-yes --max-gas 300000
echo "2. Check Sender Balance"
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
cd ..
echo "3. Check Receiver Balance"
cd evm-side/cross-erc-20
npx hardhat balance --token DMC --account $eth_default
cd ../..
echo "<<< Done. \n"

# echo ">>> Claim DMC from Move in Ethereum"
# echo "1. Transfer from Move"
# aptos move run --function-id 0x1::coin::transfer --type-args $default::native_coin::DiemCoin --args address:$cashier u64:130000$move_decimals --assume-yes --max-gas 300000
# echo "2. Claim in Ethereum"
# cd evm-side/cross-erc-20
# npx hardhat cross-claim --token DMC --receiver $eth_default
# cd ../..
# echo "3. Check Sender Balance"
# cd move_scripts
# python3 balance_of.py $default::native_coin::DiemCoin $default
# cd ..
# echo "4. Check Receiver Balance"
# cd evm-side/cross-erc-20
# npx hardhat balance --token DMC --account $eth_default
# cd ../..
# echo "<<< Done."
