import { toUtf8Bytes } from "ethers/lib/utils";
import { getCrossVmContract } from "./utils";

async function main() {
  const crossVM = await getCrossVmContract();
  console.log((await crossVM.populateTransaction.log(toUtf8Bytes("test"), { gasLimit: 3_000_000 })).data);
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
