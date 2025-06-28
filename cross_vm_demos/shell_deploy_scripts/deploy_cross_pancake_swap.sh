source ./activate_environment.sh

source ./addresses.sh
cd ../

echo ">>> Deploy Move contract."
cd move-side/coin-move
echo "1. Request faucet"
aptos account fund-with-faucet --account default --amount 99999999999$move_decimals
echo "2. Deploy contract"
aptos move publish --named-addresses coin_wrapper=default --assume-yes --max-gas 300000
cd ../..
echo "<<< Done. \n"

echo ">>> Deploy EVM contract."
cd evm-side/swap-evm
npx hardhat run scripts/deploy.ts --network localhost
cd ../..
echo "<<< Done. \n"

echo ">>> Initialize coin"
cd move_scripts
echo "1. Init mirror Eth coin"
aptos move run --function-id $default::cross_vm_coin::initialize_mirror_coin --type-args $default::mirror_coin::EthCoin --args hex:$eth_coin u8:8 --assume-yes --max-gas 300000
echo "2. Init Diem coin"
aptos move run --function-id $default::cross_vm_coin::initialize_vault_coin --type-args $default::native_coin::DiemCoin --assume-yes --max-gas 300000
cd ..
echo "<<< Done. \n"


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
cd evm-side/swap-evm
echo "5. Mint ETH(e)"
npx hardhat mint --account $eth_default --amount 1000000 --network localhost
echo "6. Check ETH(e) balance"
npx hardhat balance --token ETH --account $eth_default
cd ../..
echo "<<< Done. \n"

echo ">>> Transfer ETH from Ethereum to Move"
echo "1. Transfer from Ethereum"
cd evm-side/swap-evm
npx hardhat cross-transfer --token ETH --receiver $default --amount 170000 --network localhost
echo "2. Check Sender Balance"
npx hardhat balance --token ETH --account $eth_default --network localhost
cd ../..
echo "3. Check Receiver Balance"
cd move_scripts
python3 balance_of.py $default::mirror_coin::EthCoin $default
cd ..
echo "<<< Done. \n"


echo ">>> Transfer DMC from Move to Ethereum"
echo "1. Transfer from Move"
aptos move run --function-id $default::cross_vm_coin::deposit --type-args $default::native_coin::DiemCoin --args hex:${eth_default:2:40} u64:190000$move_decimals --assume-yes --max-gas 300000
echo "2. Check Sender Balance"
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
cd ..
echo "3. Check Receiver Balance"
cd evm-side/swap-evm
npx hardhat balance --token DMC --account $eth_default --network localhost
cd ../..
echo "<<< Done. \n"

echo ">>> Claim DMC from Move in Ethereum"
echo "1. Transfer from Move"
aptos move run --function-id 0x1::coin::transfer --type-args $default::native_coin::DiemCoin --args address:$cashier u64:130000$move_decimals --assume-yes --max-gas 300000
echo "2. Claim in Ethereum"
cd evm-side/swap-evm
npx hardhat cross-claim --token DMC --receiver $eth_default --network localhost
cd ../..
echo "3. Check Sender Balance"
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
cd ..
echo "4. Check Receiver Balance"
cd evm-side/swap-evm
npx hardhat balance --token DMC --account $eth_default --network localhost
cd ../..
echo "<<< Done."

echo ">>> Deploy swap"
echo "1. Create resource account"
aptos move run --function-id '0x1::resource_account::create_resource_account_and_fund' --args string:pancake-swap hex:${default:2:64} 'u64:10000000' --assume-yes
echo "2. Deploy contract"
cd move-side/pancake-contracts-move/pancake-swap
aptos move publish --named-addresses pancake=$swap --assume-yes --sender-account=$swap
cd ../../..
echo "3. Init swap pool"
aptos move run --function-id $swap'::router::add_liquidity' --type-args $default::native_coin::DiemCoin $default::mirror_coin::EthCoin --args u64:80000$move_decimals u64:80000$move_decimals u64:80000$move_decimals u64:80000$move_decimals --assume-yes --max-gas 300000
echo "<<< Done."

echo ">>> Test swap (Pancake)"
cd move_scripts
echo "1. Check balance"
echo "DMC balance: "`python3 balance_of.py $default::native_coin::DiemCoin $default`
echo "Eth balance: "`python3 balance_of.py $default::mirror_coin::EthCoin $default`
echo "2. swap"
aptos move run --function-id $swap'::router::swap_exact_input' --type-args $default::native_coin::DiemCoin $default::mirror_coin::EthCoin --args u64:1000$move_decimals u64:800$move_decimals --assume-yes
echo "3. Check balance"
echo "DMC balance: "`python3 balance_of.py $default::native_coin::DiemCoin $default`
echo "Eth balance: "`python3 balance_of.py $default::mirror_coin::EthCoin $default`
cd ..
echo "<<< Done. \n"

echo ">>> Test Cross VM Swap (Pancake)"
echo "1. Deploy handler"
cd move-side/swap-move
aptos move publish --named-addresses swap_wrapper=default --assume-yes --max-gas 300000
cd ../..
echo "2. Register cashier"
aptos move run --function-id $default'::swap::register_for_pool' --type-args $default::native_coin::DiemCoin $default::mirror_coin::EthCoin --assume-yes --max-gas 300000
echo "3. Check balance"
cd evm-side/swap-evm
echo "DMC balance: "`npx hardhat balance --token DMC --account $eth_default --network localhost`
echo "Eth balance: "`npx hardhat balance --token ETH --account $eth_default --network localhost`
echo "4. Swap"
npx hardhat run scripts/swap.ts --network localhost
echo "5. Check balance"
echo "DMC balance: "`npx hardhat balance --token DMC --account $eth_default --network localhost`
echo "Eth balance: "`npx hardhat balance --token ETH --account $eth_default --network localhost`
cd ../..
echo "<<< Done. \n"

#echo ">>> Test Cross VM Add/Remove Liquidity"
#cd evm-side/swap-evm
#echo "1. Check balance"
#echo "DMC balance: "`npx hardhat balance --token DMC --account $eth_default`
#echo "Eth balance: "`npx hardhat balance --token ETH --account $eth_default`
#echo "2. Add liquidity"
#npx hardhat run scripts/add_liq.ts --network localhost
#echo "3. Check balance"
#echo "DMC balance: "`npx hardhat balance --token DMC --account $eth_default`
#echo "Eth balance: "`npx hardhat balance --token ETH --account $eth_default`
#echo "4. Remove liquidity"
#npx hardhat run scripts/remove_liq.ts --network localhost
#echo "5. Check balance"
#echo "DMC balance: "`npx hardhat balance --token DMC --account $eth_default`
#echo "Eth balance: "`npx hardhat balance --token ETH --account $eth_default`
#cd ../..
#echo "<<< Done. \n"