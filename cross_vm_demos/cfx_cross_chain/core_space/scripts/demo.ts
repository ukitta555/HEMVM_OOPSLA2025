import {address, PrivateKeyAccount} from "js-conflux-sdk";
import {conflux} from "hardhat";
import {BigNumber} from "ethers";

//json automatic address substitution from compound demo

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

    const DemoContract = await conflux.getContractFactory("DemoContract");
    const demoContractDeployReceipt = await DemoContract
        .constructor()
        .sendTransaction({
            from: defaultAccount.address
        }).executed();


    const demoContractAddress = demoContractDeployReceipt.contractCreated;
    console.log("DemoContract deployed to:", demoContractAddress);


    const coreSpaceCoin = await conflux.getContractAt("CoreSpaceCoin", contractAddress.coreSpaceCoin);
    await coreSpaceCoin
        .approve(demoContractAddress, BigNumber.from(2).pow(255))
        .sendTransaction({from: defaultAccount.address})
        .executed();


    const demoContract = await conflux.getContractAt("DemoContract", demoContractAddress);


    await demoContract
        .demoDeposit20Withdraw10(
            contractAddress.coreSpaceVault,
            contractAddress.eSpaceCrossVMProxy,
            contractAddress.eSpaceRandomAddress,
            contractAddress.coreSpaceMainAddress,
            contractAddress.coreSpaceCoin
        )
        .sendTransaction({from: defaultAccount.address})
        .executed();

    console.log("Demo performed successfully!!!!!");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});