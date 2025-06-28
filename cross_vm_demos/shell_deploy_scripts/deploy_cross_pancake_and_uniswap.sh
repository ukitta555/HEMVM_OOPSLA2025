source ./activate_environment.sh

cd ../move-side/coin_move_reverse_demo
aptos move compile --named-addresses coin_wrapper=default || exit 1;
cd ../../shell_deploy_scripts/

cd ../evm-side/uniswap-and-pancake-eth-cross/
npx hardhat compile || exit 1;
cd ../../shell_deploy_scripts/

source ./addresses.sh
cd ../


echo "Request Aptos faucet for main account."
cd move-side/coin_move_reverse_demo
aptos account fund-with-faucet --account default --amount 99999999999$move_decimals
cd ../../
echo "Done."

echo "Deploy PancakeSwap helper contract for supporting total ordering of tokens"
cd move-side/pancake-contracts-move/pancake-swap
echo "1. Create resource account"
aptos move run --function-id '0x1::resource_account::create_resource_account_and_fund' --args string:pancake-swap hex:${default:2:64} 'u64:10000000' --assume-yes
echo "2. Deploy PancakeSwap for helper functions"
aptos move publish --named-addresses pancake=$swap --assume-yes --sender-account=$swap
cd ../../../
echo "Done."

echo "1. Deploy other Move contracts."
cd move-side/coin_move_reverse_demo
aptos move publish --named-addresses coin_wrapper=default --assume-yes --max-gas 300000
cd ../../
echo "<<< Done."


echo ">>> Deploy EVM contracts."
cd evm-side/uniswap-and-pancake-eth-cross
npx hardhat run scripts/deploy.ts --network localhost
cd ../..
echo "<<< Done."

echo ">>> Mint Move coins"
echo "1. Register Diem1 coin"
aptos move run --function-id 0x1::managed_coin::register --type-args $default::native_coin::DiemCoin --assume-yes
echo "2. Mint DMC1(m)"
aptos move run --function-id $default::native_coin::mint --args address:$default u64:1000000$move_decimals --assume-yes
echo "3. Check DMC1(m) balance"
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
cd ..
echo "4. Register Diem2 coin"
aptos move run --function-id 0x1::managed_coin::register --type-args $default::native_coin_2::DiemCoin2 --assume-yes
echo "5. Mint DMC2(m)"
aptos move run --function-id $default::native_coin_2::mint --args address:$default u64:1000000$move_decimals --assume-yes
echo "6. Check DMC2(m) balance"
cd move_scripts
python3 balance_of.py $default::native_coin_2::DiemCoin2 $default
cd ..
cd evm-side/uniswap-and-pancake-eth-cross
echo "4. Mint ETH(e)"
npx hardhat mint --account $eth_default --amount 1000000000
echo "5. Check ETH(e) balance"
npx hardhat balance --token ETH --account $eth_default
cd ../../
echo "<<< Done."


echo ">>> Create mirror contract from Move to Ethereum."
echo "1. Init mirror Eth coin"
aptos move run --function-id $default::cross_vm_coin_reverse_demo::initialize_mirror_coin --type-args $default::mirror_coin::EthCoin --args hex:$eth_coin u8:8 --assume-yes --max-gas 300000
aptos move run --function-id $default::cross_vm_coin_reverse_demo::initialize_vault_coin --type-args $default::native_coin::DiemCoin --assume-yes --max-gas 300000
echo "2. Register mirror Eth coin"
aptos move run --function-id 0x1::managed_coin::register --type-args $default::mirror_coin::EthCoin --assume-yes
echo "<<< Done."


echo ">>> Transfer ETH from Ethereum to Move"
echo "1. Transfer from Ethereum"
cd evm-side/uniswap-and-pancake-eth-cross
npx hardhat cross-transfer --token ETH --receiver $default --amount 170000
echo "2. Check Sender Balance"
npx hardhat balance --token ETH --account $eth_default
cd ../..
echo "3. Check Receiver Balance"
cd move_scripts
python3 balance_of.py $default::mirror_coin::EthCoin $default
cd ..
echo "<<< Done."

echo ">>> Transfer DMC from Move to Ethereum"
echo "1. Transfer from Move"
aptos move run --function-id $default::cross_vm_coin_reverse_demo::deposit --type-args $default::native_coin::DiemCoin --args hex:${eth_default:2:40} u64:190000$move_decimals --assume-yes --max-gas 300000
echo "2. Check Sender Balance"
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
cd ..
echo "3. Check Receiver Balance"
cd evm-side/uniswap-and-pancake-eth-cross
#npx hardhat balance --token ETH --account $eth_default
npx hardhat balance --token DMC --account $eth_default
cd ../..
echo "<<< Done."

echo ">>> Deploy Uniswap on ETH and try to swap"
cd evm-side/uniswap-and-pancake-eth-cross/scripts
npx hardhat run deploy_cross_uniswap.ts
cd ../../..
echo "<<< Done."



echo "Init swap pools (Pancake)"
aptos move run --function-id $swap'::router::add_liquidity' --type-args $default::native_coin::DiemCoin $default::mirror_coin::EthCoin --args u64:80000$move_decimals u64:80000$move_decimals u64:80000$move_decimals u64:80000$move_decimals --assume-yes --max-gas 300000
aptos move run --function-id $swap'::router::add_liquidity' --type-args $default::native_coin::DiemCoin $default::native_coin_2::DiemCoin2 --args u64:80000$move_decimals u64:80000$move_decimals u64:80000$move_decimals u64:80000$move_decimals --assume-yes --max-gas 300000
echo "<<< Done."

echo ">>> Connect LP tokens on both sides."
cd move-side/coin_move_reverse_demo
aptos move run --function-id $default'::cross_vm_coin_reverse_demo::register_uniswap_lp_token' --type-args $default::native_coin::DiemCoin $default::mirror_coin::EthCoin  --args hex:$cross_uniswap_pair_address u8:8 --assume-yes --max-gas 300000
cd ../..
echo "<<< Done."

echo ">>> Deploy MoveSwapRouter.sol (PancakeSwap to be called from EVM)."
cd evm-side/uniswap-and-pancake-eth-cross
npx hardhat run scripts/deploy_move_router.ts --network localhost
cd ../..
echo "<<< Done."


echo ">>> Try calling add liquidity"
echo "1. Check balance"
cd evm-side/uniswap-and-pancake-eth-cross
npx hardhat balance --token ETH --account 0x$cross_uniswap_proxy
npx hardhat balance --token DMC --account 0x$cross_uniswap_proxy
npx hardhat balance --token UNI_LP --account 0x$cross_uniswap_proxy
cd ../..
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
python3 balance_of.py $default::mirror_coin::EthCoin $default
python3 balance_of.py $default::lp_token::LPToken\<$default::mirror_coin::EthCoin\,$default::native_coin::DiemCoin\> $default
cd ../
echo "2. Call"
cd move-side/coin_move_reverse_demo
aptos move run --function-id $default"::cross_vm_coin_reverse_demo::add_liquidity" --type-args $default::native_coin::DiemCoin $default::mirror_coin::EthCoin --args u64:1000$move_decimals u64:1000$move_decimals u64:1$move_decimals u64:1$move_decimals u64:1913334000 hex:$cross_uniswap_proxy --assume-yes --max-gas 300000
cd ../..
echo "3. Check balance"
cd evm-side/uniswap-and-pancake-eth-cross
npx hardhat balance --token ETH --account 0x$cross_uniswap_proxy
npx hardhat balance --token DMC --account 0x$cross_uniswap_proxy
npx hardhat balance --token UNI_LP --account 0x$cross_uniswap_proxy
cd ../..
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
python3 balance_of.py $default::mirror_coin::EthCoin $default
python3 balance_of.py $default::lp_token::LPToken\<$default::mirror_coin::EthCoin\,$default::native_coin::DiemCoin\> $default
cd ../
echo "<<< Done."

echo ">>> Try cross swapping ExactIn"
echo "1. Check balance"
cd evm-side/uniswap-and-pancake-eth-cross
npx hardhat balance --token ETH --account 0x$cross_uniswap_proxy
npx hardhat balance --token DMC --account 0x$cross_uniswap_proxy
npx hardhat balance --token UNI_LP --account 0x$cross_uniswap_proxy
cd ../..
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
python3 balance_of.py $default::mirror_coin::EthCoin $default
python3 balance_of.py $default::lp_token::LPToken\<$default::mirror_coin::EthCoin\,$default::native_coin::DiemCoin\> $default
cd ../
echo "2. Call"
cd move-side/coin_move_reverse_demo
aptos move run --function-id $default"::cross_vm_coin_reverse_demo::swap_exact_tokens_for_tokens" --type-args $default::native_coin::DiemCoin $default::mirror_coin::EthCoin --args u64:100$move_decimals u64:10$move_decimals  u64:1913334000 hex:$cross_uniswap_proxy --assume-yes --max-gas 300000
cd ../..
echo "3. Check balance"
cd evm-side/uniswap-and-pancake-eth-cross
npx hardhat balance --token ETH --account 0x$cross_uniswap_proxy
npx hardhat balance --token DMC --account 0x$cross_uniswap_proxy
npx hardhat balance --token UNI_LP --account 0x$cross_uniswap_proxy
cd ../..
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
python3 balance_of.py $default::mirror_coin::EthCoin $default
python3 balance_of.py $default::lp_token::LPToken\<$default::mirror_coin::EthCoin\,$default::native_coin::DiemCoin\> $default
cd ../
echo "<<< Done."



echo ">>> Try calling remove liquidity"
echo "1. Check balance"
cd evm-side/uniswap-and-pancake-eth-cross
npx hardhat balance --token ETH --account 0x$cross_uniswap_proxy
npx hardhat balance --token DMC --account 0x$cross_uniswap_proxy
npx hardhat balance --token UNI_LP --account 0x$cross_uniswap_proxy
cd ../..
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
python3 balance_of.py $default::mirror_coin::EthCoin $default
python3 balance_of.py $default::lp_token::LPToken\<$default::mirror_coin::EthCoin\,$default::native_coin::DiemCoin\> $default
cd ../
echo "2. Call"
cd move-side/coin_move_reverse_demo
aptos move run --function-id $default"::cross_vm_coin_reverse_demo::remove_liquidity" --type-args $default::native_coin::DiemCoin $default::mirror_coin::EthCoin --args u64:1000$move_decimals u64:700$move_decimals u64:700$move_decimals u64:1913334000 hex:$cross_uniswap_proxy --assume-yes --max-gas 300000
# aptos move run --function-id $default"::cross_vm_coin_reverse_demo::add_liquidity_2" --type-args $default::native_coin::DiemCoin $default::mirror_coin::EthCoin --assume-yes --max-gas 300000
cd ../..
echo "3. Check balance"
cd evm-side/uniswap-and-pancake-eth-cross
npx hardhat balance --token ETH --account 0x$cross_uniswap_proxy
npx hardhat balance --token DMC --account 0x$cross_uniswap_proxy
npx hardhat balance --token UNI_LP --account 0x$cross_uniswap_proxy
cd ../..
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
python3 balance_of.py $default::mirror_coin::EthCoin $default
python3 balance_of.py $default::lp_token::LPToken\<$default::mirror_coin::EthCoin\,$default::native_coin::DiemCoin\> $default
cd ../
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
cd move-side/swap-move-with-uniswap
aptos move publish --named-addresses swap_wrapper=default --assume-yes --max-gas 300000
cd ../..
echo "2. Register cashier"
aptos move run --function-id $default'::swap::register_for_pool' --type-args $default::native_coin::DiemCoin $default::mirror_coin::EthCoin --assume-yes --max-gas 300000
echo "3. Check balance"
cd evm-side/swap-evm-double-dex
echo "DMC balance: "`npx hardhat balance --token DMC --account $eth_default`
echo "Eth balance: "`npx hardhat balance --token ETH --account $eth_default`
echo "4. Swap"
npx hardhat run scripts/swap.ts --network localhost
echo "5. Check balance"
echo "DMC balance: "`npx hardhat balance --token DMC --account $eth_default`
echo "Eth balance: "`npx hardhat balance --token ETH --account $eth_default`
cd ../..
echo "<<< Done."