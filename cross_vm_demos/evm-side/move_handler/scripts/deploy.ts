import { ethers } from "hardhat";
import { newSigner } from "./utils";

async function main() {
  let MoveHandler = await ethers.getContractFactory("MoveHandler");
  const signer = await newSigner();
  MoveHandler = await MoveHandler.connect(signer);
  const moveHandler = await MoveHandler.deploy();
  await moveHandler.deployed();

  console.log(moveHandler.address);

  // console.log(`Lock with 1 ETH and unlock timestamp ${unlockTime} deployed to ${lock.address}`);
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
