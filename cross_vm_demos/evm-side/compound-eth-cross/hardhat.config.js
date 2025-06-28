require('@nomiclabs/hardhat-web3');
require('@nomiclabs/hardhat-ethers');
const {BigNumber} = require('ethers');
const Big = require("big.js");
const { task } = require("hardhat/config");
// require('@nomiclabs/hardhat-waffle');

function toUnit(value, decimals) {
  let base = Big(10).pow(decimals);
  return BigNumber.from(base.mul(value).toFixed(0));
}

function fromUnit(value, decimals) {
  let base = Big(10).pow(decimals);
  return Big(value).div(base).toString();
}

async function tokenContract(token) {
  let tokenAddress;
  let erc20;
  if (token === "ETH") {
    tokenAddress = "0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc";
    erc20 = await ethers.getContractAt("IERC20Metadata", tokenAddress);
  } else if (token === "DMC") {
    tokenAddress = "0x5ca0f43868e106ac9aec48f8f1285896c0b9865d";
    erc20 = await ethers.getContractAt("IERC20Metadata", tokenAddress);
  } else if (token === "C_ETH") {
    tokenAddress = "0x14529a6c979b2563207e260a6138f4026b19ee0d";
    erc20 = await ethers.getContractAt("contracts/CErc20.sol:CErc20", tokenAddress);
  } else if (token === "C_DMC") {
    tokenAddress = "0x866a4a061de0f196205dff79b3c47700b570f617";
    erc20 = await ethers.getContractAt("contracts/CErc20.sol:CErc20", tokenAddress);
  } else {
    throw new Error(`Unrecognized symbol ${token}`);
  }
  return erc20
}

function portalContractAddress(token) {
  let tokenAddress;
  if (token === "ETH") {
    tokenAddress = "0x7d3d6e9f5ab582112c5cdbd712e808b2a4eafa5d";
  } else if (token === "DMC") {
    tokenAddress = "0x5ca0f43868e106ac9aec48f8f1285896c0b9865d";
  }  else {
    throw new Error(`Unrecognized symbol ${token}`);
  }
  return tokenAddress;
}
async function portalContract(token) {
  let tokenAddress = portalContractAddress(token);
  let crossErc20 = await ethers.getContractAt("ICrossVmErc20", tokenAddress);
  return crossErc20
}

async function approveCrossTransfer(token) {
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
  console.log(account)
  let erc20 = await tokenContract(token);
  let decimals = token === "C_ETH" || token === "C_DMC" ? 18 : await erc20.decimals();
  // console.log(erc20)
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

task("get-debt", "Get debt on CEthCoin")
.setAction(async () => {
  const CErc20Twin = await ethers.getContractAt("contracts/CErc20.sol:CErc20", "0x14529a6c979b2563207e260a6138f4026b19ee0d");
  const borrowBalanceStored = await CErc20Twin.borrowBalanceStored("0x812cBBdE09AF8214a5c3addE18Fcec9891196494");
  console.log(`Current EthCoin borrow amount ${borrowBalanceStored}`);
})


module.exports = {
  solidity: {
    version: '0.8.9',
    settings: {
      optimizer: {
        enabled: true,
        runs: 1000
      }
    }
  },
  defaultNetwork: "localhost",
  networks: {
    // hardhat: {
    //   forking: {
    //     url: providerUrl,
    //   },
    //   gasPrice: 0,
    //   initialBaseFeePerGas: 0,
    //   loggingEnabled: false,
    //   accounts: {
    //     mnemonic: developmentMnemonic,
    //   },
    //   chainId: 1, // metamask -> accounts -> settings -> networks -> localhost 8545 -> set chainId to 1
    // },
    localhost: {
      url: 'http://127.0.0.1:8545/',
      // accounts: getPrivateKeysFromMnemonic(developmentMnemonic),
      accounts: ["fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa"]
    }
  }
};
