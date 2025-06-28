source ./activate_environment.sh

source ./addresses.sh
cd ../



echo ">>> Deploy Move contract."
cd move-side/just-coin
echo "1. Request faucet"
aptos account fund-with-faucet --account default --amount 99999999999999
aptos account fund-with-faucet --account default2 --amount 99999999999999
echo "2. Deploy contract"
aptos move publish --named-addresses coin_wrapper=default --assume-yes --max-gas 300000
echo ">>> Mint coin"
echo "1. Register Diem coin"
aptos move run --function-id 0x1::managed_coin::register --type-args $default::native_coin::DiemCoin --assume-yes
aptos move run --function-id 0x1::managed_coin::register --type-args $default::native_coin::DiemCoin --assume-yes --profile default2
echo "2. Mint DMC(m)"
aptos move run --function-id $default::native_coin::mint --args address:$default u64:1000000$move_decimals --assume-yes
cd ../..
echo "3. Check DMC(m) balance"
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
cd ..

cd evm-side/eth-erc-20/
echo "Deploy ERC-20 token..."
npx hardhat run scripts/deploy.ts
echo "ERC-20 deployed!"


echo "<<< Done. \n"