import {ethers} from "hardhat";
async function notSoMainAfterAll() {

  const crossVMProxy = await ethers.getContractAt("CrossVmProxyReverse", "0xcC166f312524Cc88E2c16c3bdd5735a23376B1fb");


  let utf8Encode = new TextEncoder();
  let result = ethers.utils.arrayify( "0x5ca0f43868e106ac9aec48f8f1285896c0b9865d");
  console.log(result);
  // let result = utf8Encode.encode("63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc");
  // const params = ethers.utils.defaultAbiCoder.encode(
  //   ["bytes[]"], // encode as address array
  //   [result]
  // ); // array to encode
  console.log(await crossVMProxy.getTokenInfo("0x5ca0f43868e106ac9aec48f8f1285896c0b9865d"));
  // console.log(
  //     "Check whether Uniswap pair is supported by crossVM Proxy",
  //     await crossVMProxy.queryErc20Test("0x5ca0f43868e106ac9aec48f8f1285896c0b9865d", {gasLimit: 3000000}),
  //     // await crossVMProxy.queryErc20Symbol([result])
  // );
}


notSoMainAfterAll().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});