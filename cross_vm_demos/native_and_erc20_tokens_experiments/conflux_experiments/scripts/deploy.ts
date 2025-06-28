import {conflux} from "hardhat";
import {Conflux, Contract, PrivateKeyAccount} from "js-conflux-sdk";

async function main() {
  // let Proxy = await hre.conflux.getContractFactory("CrossVmProxy");
  // const proxy = await Proxy.deploy({gasLimit: 30000000});
  // await proxy.deployed();

  // console.log(`Deploy proxy at ${proxy.address}`);
  const signers: PrivateKeyAccount[] = await conflux.getSigners();
  const defaultAccount = signers[0];

  let CoreSpaceCoin: Contract = await conflux.getContractFactory("CoreSpaceCoin");
  const deployReceipt = await CoreSpaceCoin.constructor().sendTransaction({
    from: defaultAccount.address
  }).executed();

  const coreSpaceCoinAddress = deployReceipt.contractCreated;
  console.log("CoreSpaceCoin deployed to:", coreSpaceCoinAddress);

  const coreSpaceCoin: Contract = await conflux.getContractAt('CoreSpaceCoin', coreSpaceCoinAddress);

  await coreSpaceCoin
      .mint(defaultAccount.address, 10000 * 10 ** 18)
      .sendTransaction({
        from: defaultAccount.address
      }).executed();

  console.log(`Minted 10000 CoreSpaceCoin to the ${defaultAccount.address} address`);
  // let SwapRouter = await ethers.getContractFactory("MoveSwapRouter");
  // const router = await SwapRouter.deploy(proxy.address, {gasLimit: 30000000})
  // await router.deployed();
  //
  // console.log(`Deploy swap at ${router.address}`);
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
