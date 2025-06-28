import { arrayify } from "ethers/lib/utils";
import { getCrossVmContract } from "./utils";

async function main() {
  const crossVM = await getCrossVmContract();
  const receiver = arrayify(
    "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
  );
  const module = "hello";
  const func = "hello_with_type_info";
  const aptos_framework = arrayify(
    "0x0000000000000000000000000000000000000000000000000000000000000001"
  );
  const type = {addr: aptos_framework, module: "aptos_coin", type_name: "AptosCoin"}

  await crossVM.callMove(receiver, module, func, [], [type], { gasLimit: 3_000_000 });
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
