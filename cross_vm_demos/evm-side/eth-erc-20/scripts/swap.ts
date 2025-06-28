import { BigNumber } from "ethers";
import { ethers } from "hardhat";
import Big from "big.js";
import { IERC20Metadata } from "../typechain-types";

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
  } else {
    throw new Error(`Unrecognized symbol ${token}`);
  }
  let erc20 = await ethers.getContractAt("IERC20Metadata", tokenAddress);
  return erc20;
}

async function main() {
  let swap = await ethers.getContractAt(
    "MoveSwapRouter",
    "0x812cBBdE09AF8214a5c3addE18Fcec9891196494"
  );

  let eth = await tokenContract("ETH");
  let emc = await tokenContract("DMC");

  await eth.approve(swap.address, toUnit(100000, 18));
  await swap.approvePortal(eth.address);

  // let tx = await swap.swapExactTokensForTokens(eth.address, emc.address, toUnit(1000,18), toUnit(800,18), {gasLimit: 30000000})
  let tx = await swap.swapTokensForExactTokens(
    eth.address,
    emc.address,
    toUnit(1000, 18),
    toUnit(1200, 18),
    { gasLimit: 30000000 }
  );
  const receipt = await tx.wait();
  console.log(receipt)
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
