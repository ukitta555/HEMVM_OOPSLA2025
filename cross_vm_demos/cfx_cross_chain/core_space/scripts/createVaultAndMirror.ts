import {address, PrivateKeyAccount} from "js-conflux-sdk";
import {conflux} from "hardhat";
import {ethers} from "ethers";

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

    const crossSpaceProxyCore = await conflux.getContractAt("CrossVmProxyCFX", contractAddress.coreSpaceCrossVmProxy);

    await crossSpaceProxyCore
        .changeHandler(contractAddress.eSpaceCrossVMProxy)
        .sendTransaction({from: defaultAccount.address})
        .executed();

    // console.log(result);


    console.log("Address of the (soon to be created) mirror contract");
    let result = await crossSpaceProxyCore
        .generateVaultAndMirrorForToken(contractAddress.coreSpaceCoin)
        .call({from: defaultAccount.address});

    contractAddress.eSpaceMirrorAddress = '0x' + result.toString('hex').substring(0, 42);

    await crossSpaceProxyCore
        .generateVaultAndMirrorForToken(contractAddress.coreSpaceCoin)
        .sendTransaction({from: defaultAccount.address})
        .executed();

    console.log("Vault and mirror token created!");

    printContractAddress()
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});