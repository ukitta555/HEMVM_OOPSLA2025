const { ethers } = require("hardhat");

async function main() {
  let Proxy = await ethers.getContractFactory("CrossVmProxyCompound");
  const proxy = await Proxy.deploy({gasLimit: 30000000});
  await proxy.deployed();
  console.log(`Deploy proxy at ${proxy.address}`);

  let EthCoin = await ethers.getContractFactory("EthCoin");
  const ecoin = await EthCoin.deploy({gasLimit: 30000000});
  await ecoin.deployed();

  console.log(`Deploy coin at ${ecoin.address}`);

  let CrossCompoundWrapper = await ethers.getContractFactory("CrossCompoundWrapper");
  const crossCompoundWrapper = await CrossCompoundWrapper.deploy({gasLimit: 30000000});
  await crossCompoundWrapper.deployed();

  console.log(`Deploy wrapper at ${crossCompoundWrapper.address}`);
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
