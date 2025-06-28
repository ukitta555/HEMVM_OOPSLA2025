import {PrivateKeyAccount} from "js-conflux-sdk";
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

    const coreSpaceCoin = await conflux.getContractAt("CoreSpaceCoin", contractAddress.coreSpaceCoin);
    const crossSpaceProxyCore = await conflux.getContractAt("CrossVmProxyCFX", contractAddress.coreSpaceCrossVmProxy);

    const vaultAddress =
        await crossSpaceProxyCore
            .tokenToPortal(contractAddress.coreSpaceCoin);
    console.log("Vault address:", vaultAddress);
    contractAddress.coreSpaceVault = vaultAddress;

    const vault = await conflux.getContractAt("VaultErc20", contractAddress.coreSpaceVault);

    await coreSpaceCoin
        .approve(vault.address, BigNumber.from(2).pow(255))
        .sendTransaction({from: defaultAccount.address})
        .executed();

    console.log("Approved token transfer");

    let result =
        await vault
            .deposit(contractAddress.eSpaceCrossVMProxy, 10 * (10 ** 18))
            .sendTransaction({from: defaultAccount.address})
            .executed();


    console.log("Deposited CoreSpaceCoins cross-chain!!!!!");
    printContractAddress();
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});