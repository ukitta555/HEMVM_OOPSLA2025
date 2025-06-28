import { HardhatUserConfig, task } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import "hardhat-conflux";
// import { ethers } from "hardhat";
import { BigNumber } from "ethers";
import Big from "big.js";
import { IERC20Metadata, ICrossVmErc20 } from "./typechain-types";
import {Contract} from "js-conflux-sdk";


function toUnit(value: number, decimals: number): BigNumber {
  let base = Big(10).pow(decimals);
  return BigNumber.from(base.mul(value).toFixed(0));
}

function fromUnit(value: BigNumber, decimals: number): string {
  let base = BigNumber.from(10).pow(decimals);
  return BigNumber.from(value).div(base).toString();
}

task("core-space-coin-balance", "Prints an account's CoreSpaceCoin balance")
    .addParam("tokenaddr", "The token's address")
    .addParam("account", "The account's address")
    .setAction(async ({tokenaddr, account}) => {
      let coin: Contract = await conflux.getContractAt('CoreSpaceCoin', tokenaddr);
      let decimals = await coin.decimals();
      console.log(`Coin's decimals: ${decimals}`);
      console.log("User's balance:", fromUnit(await coin.balanceOf(account), decimals));
    })

// task("token-info", "Transfer token to another space")
// .setAction(async () => {
//   let protal = await portalContract("ETH");
//   let proxy = await ethers.getContractAt("CrossVmProxy", "0xcC166f312524Cc88E2c16c3bdd5735a23376B1fb")
//   console.log(await proxy.tokenInfo(protal.address))
// })

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.17",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  defaultNetwork: "localhost",
  networks: {
    localhost: {
      url:"http://127.0.0.1:12537/",
      accounts: ["fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa"],
      chainId: 1,
    }
  }
};

export default config;
