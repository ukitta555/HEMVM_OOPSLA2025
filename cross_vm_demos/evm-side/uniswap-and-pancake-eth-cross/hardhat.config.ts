import { HardhatUserConfig, task } from "hardhat/config";
import { BigNumber } from "ethers";
import Big from "big.js";
import { IERC20Metadata, ICrossVmErc20 } from "./typechain-types";
import '@typechain/hardhat';
import '@nomiclabs/hardhat-ethers';
import '@nomiclabs/hardhat-waffle';

function toUnit(value: number, decimals: number): BigNumber {
  let base = Big(10).pow(decimals);
  return BigNumber.from(base.mul(value).toFixed(0));
}

function fromUnit(value: BigNumber, decimals: number): BigNumber {
  let base = Big(10).pow(decimals);
  return Big(value).div(base).toString();
}

async function tokenContract(token: string): Promise<IERC20Metadata> {
  let tokenAddress;
  if (token === "ETH") {
    tokenAddress = "0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc";
  } else if (token === "DMC") {
    tokenAddress = "0x5ca0f43868e106ac9aec48f8f1285896c0b9865d";
  } else if (token == "UNI_LP") {
    tokenAddress = "0x45bAAe478B597a3d1a6C90eDFBa8b52eaeAc6043";
  } else {
    throw new Error(`Unrecognized symbol ${token}`);
  }
  let erc20 = await ethers.getContractAt("IERC20Metadata", tokenAddress);
  return erc20
}

function portalContractAddress(token: string): string {
  let tokenAddress;
  if (token === "ETH") {
    tokenAddress = "0x7d3d6e9f5ab582112c5cdbd712e808b2a4eafa5d";
  } else if (token === "DMC") {
    tokenAddress = "0x5ca0f43868e106ac9aec48f8f1285896c0b9865d";
  } else if (token == "UNI_LP") {
    tokenAddress = "0xef9a4fcb2bfa7160719fdbdff8f86f02246d65b3";
  } else {
    throw new Error(`Unrecognized symbol ${token}`);
  }
  return tokenAddress;
}
async function portalContract(token: string): Promise<ICrossVmErc20> {
  let tokenAddress = portalContractAddress(token);
  let crossErc20 = await ethers.getContractAt("ICrossVmErc20", tokenAddress);
  return crossErc20
}

async function approveCrossTransfer(token: string) {
  let erc20 = await tokenContract(token);
  let portal = portalContractAddress(token);
  await erc20.approve(portal, BigNumber.from(2).pow(255));
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

task("cross-transfer", "Transfer token to another space")
.addParam("token", "The token symbol")
.addParam("receiver", "The receiver address in Move space")
.addParam("amount", "The transfer amount")
.setAction(async ({token, receiver, amount}) => {
  await approveCrossTransfer(token);
  let erc20 = await tokenContract(token);
  let portal = await portalContract(token);
  let decimals = await erc20.decimals();
  console.log("decimals", decimals);
  await portal.deposit(receiver, toUnit(amount, decimals), {gasLimit: 30000000});
  console.log("deposit function called ( check node output for more info, no guarantees of success ;) )")
})

task("cross-claim", "Transfer token to another space")
.addParam("token", "The token symbol")
.addParam("receiver", "The receiver address in Move space")
.setAction(async ({token, receiver, amount}) => {
  await approveCrossTransfer(token);
  let portal = await portalContract(token);

  await portal.withdraw(receiver, {gasLimit: 30000000});
})


const config: HardhatUserConfig = {
  solidity: {
    compilers: [
      {
        version: '0.5.16',
        settings: {
          optimizer: {
            enabled: true,
            runs: 200,
          },
        },
      },
      {
        version: '0.6.6',
        settings: {
          optimizer: {
            enabled: true,
            runs: 200,
          },
        },
      },
    ],
    overrides: {
      "contracts/cross_space/coin/EthCoin.sol": { version: "0.8.17", settings: {optimizer: {enabled: true,  runs: 200}} },
      "contracts/cross_space/coin/MirrorErc20.sol": { version: "0.8.17", settings: {optimizer: {enabled: true,  runs: 200}} },
      "contracts/cross_space/interfaces/ICrossVmErc20.sol": { version: "0.8.17", settings: {optimizer: {enabled: true,  runs: 200}} },
      "contracts/cross_space/swap/MoveSwapRouter.sol": { version: "0.8.17", settings: {optimizer: {enabled: true,  runs: 200}} },
      "contracts/cross_space/swap/CrossUniswapWrapper.sol": { version: "0.8.17", settings: {optimizer: {enabled: true,  runs: 200}} },
      "contracts/cross_space/interfaces/ICrossVM.sol": { version: "0.8.17", settings: {optimizer: {enabled: true,  runs: 200}} },
      "contracts/cross_space/coin/CrossVmProxyReverse.sol": { version: "0.8.17", settings: {optimizer: {enabled: true,  runs: 200}} },
      "contracts/cross_space/coin/VaultErc20.sol": { version: "0.8.17", settings: {optimizer: {enabled: true,  runs: 200}} },
      "contracts/cross_space/interfaces/ICrossVmErc20Proxy.sol": { version: "0.8.17", settings: {optimizer: {enabled: true,  runs: 200}} },
      "contracts/cross_space/coin/CrossVmProxy.sol": { version: "0.8.17", settings: {optimizer: {enabled: true,  runs: 200}} },
      "contracts/cross_space/@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol": { version: "0.8.17", settings: { } },
      "contracts/cross_space/@openzeppelin/contracts/token/ERC20/IERC20.sol": { version: "0.8.17", settings: { } },
      "contracts/cross_space/@openzeppelin/contracts/interfaces/IERC20.sol": { version: "0.8.17", settings: { } },
      "contracts/cross_space/@openzeppelin/contracts/interfaces/IERC20Metadata.sol": { version: "0.8.17", settings: { } },
      "contracts/cross_space/@openzeppelin/contracts/utils/Context.sol": { version: "0.8.17", settings: { } },
      "contracts/cross_space/@openzeppelin/contracts/access/Ownable.sol": { version: "0.8.17", settings: { } },
      "contracts/cross_space/@openzeppelin/contracts/token/ERC20/ERC20.sol": { version: "0.8.17", settings: { } },
    }

  },
  defaultNetwork: "localhost",
  networks: {
    localhost: { url:"http://127.0.0.1:8545/", accounts: ["fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa"] }
  }
};

export default config;
