import {conflux} from "hardhat";
import {address, Conflux, Contract, PrivateKeyAccount} from "js-conflux-sdk";

async function main() {
    const signers: PrivateKeyAccount[] = await conflux.getSigners();
    const defaultAccount = signers[0];
    console.log("Core address:", defaultAccount.address)
    const crossSpaceCall = conflux.InternalContract("CrossSpaceCall");

    const result = await crossSpaceCall.mappedBalance(defaultAccount.address);
    console.log("User's balance:", result);
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
