import {PrivateKeyAccount} from "js-conflux-sdk";
import {conflux} from "hardhat";

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

    const crossSpaceProxyCore = await conflux.getContractAt("CrossVmProxyCFX", contractAddress.coreSpaceCrossVmProxy);

    const vaultAddress =
        await crossSpaceProxyCore
            .tokenToPortal(contractAddress.coreSpaceCoin);
    console.log("Vault address:", vaultAddress);

    const vault = await conflux.getContractAt("VaultErc20", contractAddress.coreSpaceVault);

    await vault
        .withdraw(contractAddress.coreSpaceMainAddress)
        .sendTransaction({from: defaultAccount.address})
        .executed();

    console.log("Withdrew CoreSpaceCoins cross-chain!!!!!");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});