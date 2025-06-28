from aptos_sdk.async_client import RestClient, FaucetClient

# test_account = Account.load_key("0xfafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa")
# test_address = test_account.account_address

rest_client = RestClient("http://127.0.0.1:8080/v1")
faucet_client = FaucetClient("http://127.0.0.1:8081/", rest_client)