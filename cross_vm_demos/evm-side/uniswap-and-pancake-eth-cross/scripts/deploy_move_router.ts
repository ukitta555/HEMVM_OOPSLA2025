import { ethers } from "hardhat";

async function main() {
    let SwapRouter = await ethers.getContractFactory("MoveSwapRouter");
    const router = await SwapRouter.deploy("0xcC166f312524Cc88E2c16c3bdd5735a23376B1fb", {gasLimit: 30000000})
    await router.deployed();
  
    console.log(`Deploy swap at ${router.address}`);
}


main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
  
  