source ./addresses.sh
cd ../

echo "1. Request faucet"
aptos account fund-with-faucet --account default --amount 9999999999999
aptos account fund-with-faucet --account default2 --amount 9999999999999