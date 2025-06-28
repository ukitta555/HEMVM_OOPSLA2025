import { arrayify, parseEther } from "ethers/lib/utils";
import { getCrossVmContract } from "./utils";

async function main() {
  const crossVM = await getCrossVmContract();
  const receiver = arrayify(
    "0x695afb3d2378ae743b45a95065a28d093dc03a0f14389799552f7ab0cdee2b77"
  );
  const module = "";
  const func = "";

  await crossVM.callMove(receiver, module, func, [], [], { gasLimit: 3_000_000, value: parseEther("1") });

  console.log(`transfer 1 coin to 0x695afb3d2378ae743b45a95065a28d093dc03a0f14389799552f7ab0cdee2b77`)
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
