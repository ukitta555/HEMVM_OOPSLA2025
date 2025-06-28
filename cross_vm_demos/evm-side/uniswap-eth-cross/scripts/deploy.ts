import { ethers } from "hardhat";

async function main() {
  let Proxy = await ethers.getContractFactory("CrossVmProxyReverse");
  const proxy = await Proxy.deploy({gasLimit: 30000000});
  await proxy.deployed();
  console.log(`Deploy proxy for reverse demo at ${proxy.address}`);

  let EthCoin = await ethers.getContractFactory("EthCoin");
  const ecoin = await EthCoin.deploy({gasLimit: 30000000});
  await ecoin.deployed();

  console.log(`Deploy coin at ${ecoin.address}`);

  let CrossUniswapWrapper = await ethers.getContractFactory("CrossUniswapWrapper");
  const crossUniswapWrapper = await CrossUniswapWrapper.deploy({gasLimit: 30000000});
  await crossUniswapWrapper.deployed();

  console.log(`Deploy Cross Uniswap Proxy at ${crossUniswapWrapper.address}`);
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
