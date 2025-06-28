import { ethers } from "hardhat";

async function main() {
  let Proxy = await ethers.getContractFactory("CrossVmProxy");
  const proxy = await Proxy.deploy({gasLimit: 30000000});
  await proxy.deployed();

  console.log(`Deploy proxy at ${proxy.address}`);

  let EthCoin = await ethers.getContractFactory("EthCoin");
  const ecoin = await EthCoin.deploy();
  await ecoin.deployed();

  console.log(`Deploy coin at ${ecoin.address}`);

  let SwapRouter = await ethers.getContractFactory("MoveSwapRouter");
  const router = await SwapRouter.deploy(proxy.address, {gasLimit: 30000000})
  await router.deployed();

  console.log(`Deploy swap at ${router.address}`);
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
