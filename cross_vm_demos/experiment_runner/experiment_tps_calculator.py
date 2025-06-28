results_seconds = {
    'salad_55_35_10_ERC20_custom_coin_500k': [149.101772029],
    'salad_60_40_ERC20_custom_coin_500k': [101.394161352],
    'salad_70_20_10_native_coin': [84.568224963],
    'salad_80_20_native_coin': [58.993156164]
 }

# results_seconds = {
#     'eth_erc20_cross': [392.712725316],
#     'eth_erc20_intra': [92.31205775],
#     'eth_native_token_cross': [241.594465514],
#     'eth_native_token_intra': [44.524028429],
#     'move_coin_cross': [480.860982192],
#     'move_coin_intra': [140.985032935],
#     'move_native_token_cross': [129.967044111],
#     'move_native_token_intra': [134.236913806],
#     'salad_55_35_10_ERC20_custom_coin_500k': [149.365273274],
#     'salad_60_40_ERC20_custom_coin_500k': [100.403464486],
#     'salad_70_20_10_native_coin': [87.280663258],
#     'salad_80_20_native_coin': [60.56289574]
# }



K = 1000

for k,v in results_seconds.items():
    print(f"key: {k}, tps: {(500 * K) / v[0]}")