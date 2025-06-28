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

async function tokenContract(token: string): Promise<IERC20Metadata> {
  let tokenAddress;
  if (token === "ETH") {
    tokenAddress = "0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc";
  } else if (token === "DMC") {
    tokenAddress = "0x5ca0f43868e106ac9aec48f8f1285896c0b9865d";
  } else {
    throw new Error(`Unrecognized symbol ${token}`);
  }
  let erc20 = await ethers.getContractAt("IERC20Metadata", tokenAddress);
  return erc20
}

async function portalContract(token: string): Promise<ICrossVmErc20> {
  let tokenAddress;
  if (token === "ETH") {
    tokenAddress = "0x7d3d6e9f5ab582112c5cdbd712e808b2a4eafa5d";
  } else if (token === "DMC") {
    tokenAddress = "0x5ca0f43868e106ac9aec48f8f1285896c0b9865d";
  } else {
    throw new Error(`Unrecognized symbol ${token}`);
  }
  let crossErc20 = await ethers.getContractAt("ICrossVmErc20", tokenAddress);
  return crossErc20
}

async function approveCrossTransfer() {
  let erc20 = await tokenContract("ETH");
  let portalContract = "0x7d3d6e9f5ab582112c5cdbd712e808b2a4eafa5d";
  await erc20.approve(portalContract, BigNumber.from(2).pow(255));

}

task("mint", "Mint tokens for address")
.addParam("account", "The account's address")
.addParam("amount", "The mint amount")
.setAction(async ({account, amount}) => {
  let ethAddress = "0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc";
  let erc20 = await ethers.getContractAt("EthCoin", ethAddress);
  let decimals = await erc20.decimals();
  await erc20.mint(account, toUnit(amount, decimals));
})

task("balance", "Prints an account's balance")
.addParam("token", "The token symbol")
.addParam("account", "The account's address")
.setAction(async ({token, account}) => {
  let erc20 = await tokenContract(token);
  let decimals = await erc20.decimals();
  console.log(fromUnit(await erc20.balanceOf(account), decimals));
})

task("balanceNative", "Prints an account's balance in CFX")
    .addParam("account", "The account's address")
    .setAction(async ({account}) => {
        console.log(await ethers.provider.getBalance(account))
    })

task("cross-transfer", "Transfer token to another space")
.addParam("token", "The token symbol")
.addParam("receiver", "The receiver address in Move space")
.addParam("amount", "The transfer amount")
.setAction(async ({token, receiver, amount}) => {
  await approveCrossTransfer();
  let erc20 = await tokenContract(token);
  let protal = await portalContract(token);
  let decimals = await erc20.decimals();

  await protal.deposit(receiver, toUnit(amount, decimals), {gasLimit: 30000000});
})

task("cross-claim", "Transfer token to another space")
.addParam("token", "The token symbol")
.addParam("receiver", "The receiver address in Move space")
.setAction(async ({token, receiver, amount}) => {
  await approveCrossTransfer();
  let protal = await portalContract(token);

  await protal.withdraw(receiver, {gasLimit: 30000000});
})

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
      url:"http://127.0.0.1:8545/",
      accounts: ["fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa"],
      chainId: 1337,
    }
  }
};

export default config;
