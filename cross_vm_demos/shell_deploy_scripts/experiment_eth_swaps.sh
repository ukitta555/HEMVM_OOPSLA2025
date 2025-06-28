source ./addresses.sh

echo ">>> 1. Mint ETH(e) to the default ETH account to run the experiment."
cd evm-side/swap-evm
npx hardhat mint --account $eth_default --amount 10000000
echo "Minted. Check ETH(e) balance:"
npx hardhat balance --token ETH --account $eth_default
cd ../..
echo "<<< Done."

echo ">>> 2. Mint DMC(m) to the default Move account to run the experiment."
aptos move run --function-id $default::native_coin::mint --args address:$default u64:10000000$move_decimals --assume-yes
echo "Minted. Check DMC(m) balance:"
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
cd ..
echo "<<< Done."

echo ">>> 3. Move DMC(m) to DMC(e)."
echo "1. Transfer from Move"
aptos move run --function-id $default::cross_vm_coin::deposit --type-args $default::native_coin::DiemCoin --args hex:${eth_default:2:40} u64:10000000$move_decimals --assume-yes --max-gas 300000
echo "2. Check Sender Balance"
cd move_scripts
python3 balance_of.py $default::native_coin::DiemCoin $default
cd ..
echo "3. Check Receiver Balance"
cd evm-side/swap-evm
npx hardhat balance --token DMC --account $eth_default
cd ../..
echo "<<< Done. \n"

echo ">>> Test Cross VM Add/Remove Liquidity"
cd evm-side/swap-evm
echo "1. Check balance"
echo "DMC balance: "`npx hardhat balance --token DMC --account $eth_default`
echo "Eth balance: "`npx hardhat balance --token ETH --account $eth_default`
echo "2. Add liquidity"
npx hardhat run scripts/add_liq_a_lot.ts --network localhost
echo "3. Check balance"
echo "DMC balance: "`npx hardhat balance --token DMC --account $eth_default`
echo "Eth balance: "`npx hardhat balance --token ETH --account $eth_default`

#echo ">>> 3. Perform the experiment."
#python ./eth_experiment_uniswap/eth_swap_experiment.py
#echo "<<< Done."



