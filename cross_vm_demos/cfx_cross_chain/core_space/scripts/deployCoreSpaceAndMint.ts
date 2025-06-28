import {conflux} from "hardhat";
import {Conflux, Contract, PrivateKeyAccount} from "js-conflux-sdk";
const fs = require('fs');

// contract addresses
let contractAddress;

try {
  contractAddress = require(__dirname +
      `/../contractAddress.json`);
} catch (e) {
  contractAddress = {};
}
function printContractAddress() {
  fs.writeFileSync(
      __dirname + `/../contractAddress.json`,
      JSON.stringify(contractAddress, null, '\t'),
  );
}

async function main() {
  const signers: PrivateKeyAccount[] = await conflux.getSigners();
  const defaultAccount = signers[0];

  contractAddress.coreSpaceMainAddress = defaultAccount.address;
  contractAddress.eSpaceMappedAddress = "0xF2D76a4a43C7949a09d6CB90d66191a0B4cdFb9F"; // todo: fix this constant and make it dynamic
  contractAddress.eSpaceRandomAddress = "0x14Dcb427A216216791fB63973c5b13878de30916";

  // Deploy CrossVMProxyCFX
  let CrossVmProxy = await conflux.getContractFactory("CrossVmProxyCFX");
  const proxyDeployReceipt = await CrossVmProxy.constructor().sendTransaction({
    from: defaultAccount.address
  }).executed();
  const crossVmProxyAddress = proxyDeployReceipt.contractCreated;
  console.log("CrossVmProxy deployed to:", crossVmProxyAddress);
  contractAddress.coreSpaceCrossVmProxy = crossVmProxyAddress;

  // Deploy CoreSpaceCoin
  let CoreSpaceCoin: Contract = await conflux.getContractFactory("CoreSpaceCoin");
  const deployReceipt = await CoreSpaceCoin.constructor().sendTransaction({
    from: defaultAccount.address
  }).executed();

  const coreSpaceCoinAddress = deployReceipt.contractCreated;
  console.log("CoreSpaceCoin deployed to:", coreSpaceCoinAddress);

  contractAddress.coreSpaceCoin = coreSpaceCoinAddress;

  // Mint CoreSpaceCoin tokens
  const coreSpaceCoin: Contract = await conflux.getContractAt('CoreSpaceCoin', coreSpaceCoinAddress);

  await coreSpaceCoin
      .mint(defaultAccount.address, 10000 * 10 ** 18)
      .sendTransaction({
        from: defaultAccount.address
      }).executed();

  console.log(`Minted 10000 CoreSpaceCoin to the ${defaultAccount.address} address`);
  printContractAddress();
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
