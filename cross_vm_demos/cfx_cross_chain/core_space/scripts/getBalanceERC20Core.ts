import {conflux} from "hardhat";
import {address, Conflux, Contract, PrivateKeyAccount} from "js-conflux-sdk";

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

    const coreSpaceCoin = await conflux.getContractAt("CoreSpaceCoin", contractAddress.coreSpaceCoin);

    const result = await coreSpaceCoin.balanceOf(defaultAccount.address);
    console.log("User's CoreSpaceCoin balance:", result);
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
