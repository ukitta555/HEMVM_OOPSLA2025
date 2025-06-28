import asyncio
from common import rest_client

import sys


async def get_balance(coin_type, address):
    print(f"Getting Aptos balance for {coin_type} at address {address}...")
    type_addr = coin_type.split("::")[0]
    balance = await rest_client.account_resource(
        address,
        f"0x1::coin::CoinStore<{coin_type}>",
    )
    info = await rest_client.account_resource(
        type_addr,
        f"0x1::coin::CoinInfo<{coin_type}>",
    )
    ans = int(balance["data"]["coin"]["value"]) / pow(10, info["data"]["decimals"])
    print(ans)


if __name__ ==  '__main__':
    asyncio.run(get_balance(sys.argv[1], sys.argv[2]))

