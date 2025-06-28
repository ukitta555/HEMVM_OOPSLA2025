import { arrayify } from "ethers/lib/utils";
import { getCrossVmContract } from "./utils";

async function main() {
  const crossVM = await getCrossVmContract();
  const receiver = arrayify(
    "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
  );
  const module = "hello";
  const func = "hello";

  await crossVM.callMove(receiver, module, func, [], [], { gasLimit: 3_000_000 });
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
