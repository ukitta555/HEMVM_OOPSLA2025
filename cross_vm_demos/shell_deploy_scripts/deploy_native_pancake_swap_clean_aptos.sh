source ./activate_environment.sh

source ./addresses.sh

cd ../
echo ">>> Deploy Move coin contracts."
cd move-side/coin-move-no-crossvm
echo "1. Request faucet"
aptos account fund-with-faucet --account default --amount 999999999$move_decimals
echo "2. Deploy contract"
aptos move publish --named-addresses coin_wrapper=default --assume-yes --max-gas 300000
cd ../..
echo "<<< Done. \n"


echo ">>> Mint coin"
echo "1. Register Diem1 coin"
aptos move run --function-id 0x1::managed_coin::register --type-args $default::native_coin::DiemCoin --assume-yes
echo "2. Register Diem2 coin"
aptos move run --function-id 0x1::managed_coin::register --type-args $default::native_coin_2::DiemCoin2 --assume-yes
echo "3. Mint DMC1(m)"
aptos move run --function-id $default::native_coin::mint --args address:$default u64:1000000$move_decimals --assume-yes
echo "4. Check DMC1(m) balance"
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
cd ..
echo "5. Mint DMC2(m)"
aptos move run --function-id $default::native_coin_2::mint --args address:$default u64:1000000$move_decimals --assume-yes
echo "6. Check DMC2(m) balance"
cd move_scripts
python3 balance_of.py $default::native_coin_2::DiemCoin2 $default
cd ..
echo "<<< Done. \n"

echo ">>> Deploy swap"
echo "1. Create resource account"
aptos move run --function-id '0x1::resource_account::create_resource_account_and_fund' --args string:pancake-swap hex:${default:2:64} 'u64:10000000' --assume-yes
echo "2. Deploy contract"
cd move-side/pancake-contracts-move/pancake-swap
aptos move publish --named-addresses pancake=$swap --assume-yes --sender-account=$swap
cd ../../..
echo "3. Init swap pool"
aptos move run --function-id $swap'::router::add_liquidity' --type-args $default::native_coin::DiemCoin $default::native_coin_2::DiemCoin2 --args u64:80000$move_decimals u64:80000$move_decimals u64:80000$move_decimals u64:80000$move_decimals --assume-yes --max-gas 300000
echo "<<< Done. \n"

echo ">>> Test swap"
cd move_scripts
echo "1. Check balance"
echo "DMC balance: "`python3 balance_of.py $default::native_coin::DiemCoin $default`
echo "Eth balance: "`python3 balance_of.py $default::native_coin_2::DiemCoin2 $default`
echo "2. swap"
aptos move run --function-id $swap'::router::swap_exact_input' --type-args $default::native_coin::DiemCoin $default::native_coin_2::DiemCoin2 --args u64:1000$move_decimals u64:800$move_decimals --assume-yes
echo "3. Check balance"
echo "DMC balance: "`python3 balance_of.py $default::native_coin::DiemCoin $default`
echo "Eth balance: "`python3 balance_of.py $default::native_coin_2::DiemCoin2 $default`
cd ..
echo "<<< Done. \n"
