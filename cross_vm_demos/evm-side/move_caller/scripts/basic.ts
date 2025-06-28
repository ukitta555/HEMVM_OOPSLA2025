import { arrayify, parseEther, toUtf8Bytes } from "ethers/lib/utils";
import { ethers } from "hardhat";
import { ICrossVM } from "../typechain-types";
import { getCrossVmContract, newSigner } from "./utils";

async function hello() {
  const crossVM = await getCrossVmContract();
  await crossVM.log(toUtf8Bytes("test"), { gasLimit: 3_000_000 });
}

async function crossVMCall() {
  const crossVM = await getCrossVmContract();
  const receiver = arrayify(
    "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06"
  );
  const module = "hello_world";
  const func = "hello";
  const data = arrayify("0x");

  await crossVM.callMove(receiver, module, func, data, { gasLimit: 3_000_000 });
}

async function crossVMTransfer() {
  const crossVM = await getCrossVmContract();
  const receiver = arrayify(
    "0xfafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa"
  );
  const module = "";
  const func = "";
  const data = arrayify("0x");

  await crossVM.callMove(receiver, module, func, data, { gasLimit: 3_000_000, value: parseEther("1") });
}
export {
  hello, crossVMCall, crossVMTransfer,
}
// async function main() {  
// }

// // We recommend this pattern to be able to use async/await everywhere
// // and properly handle errors.
// main().catch((error) => {
//   console.error(error);
//   process.exitCode = 1;
// });
