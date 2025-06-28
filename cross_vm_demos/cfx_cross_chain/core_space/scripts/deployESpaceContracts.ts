import {conflux, ConfluxSDK} from "hardhat";
import {address, PrivateKeyAccount} from "js-conflux-sdk";
import {CFX_PROXY_BYTECODE} from "../consts";
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

    const crossSpaceCall = await conflux.InternalContract("CrossSpaceCall");

    // increased allowed gas per block in node config so that the bytecode fits in the gas constraints
    console.log("Address of the (soon to be deployed) proxy contract:");
    let addressProxy = await crossSpaceCall
        .createEVM(CFX_PROXY_BYTECODE)
        .call({from: defaultAccount.address, gas: 200_000_000})


    await crossSpaceCall
        .createEVM(CFX_PROXY_BYTECODE)
        .sendTransaction({from: defaultAccount.address, gas: 200_000_000})
        .executed()

    contractAddress.eSpaceCrossVMProxy = '0x' + addressProxy.toString('hex').substring(0, 42);

    console.log("Deployed the proxy to the eSpace!!!")


    // Vlad: Conflux has some weird shenanigans for msg.sender in eSpace... (mapped address + large zero padding)
    // can't use callEVM to re-set the built-in caller, simulation fails no matter how I try
    // don't have the time right now to dig in the code to understand why is msg.sender > 42 chars after fetching callEVM result
    // todo: fix access control for eSpace handlers

    // let ABI = [ "function owner()" ];
    // let iface = new ethers.utils.Interface(ABI);
    // let encodedFunctionData = iface.encodeFunctionData(
    //     "owner",
    //     []
    // )
    //
    // console.log("Current owner of espace proxy");
    // await crossSpaceCall
    //     .callEVM(contractAddress.eSpaceCrossVMProxy, encodedFunctionData)
    //     .call({from: defaultAccount.address});
    //
    //
    //
    // ABI = [ "function changeBuiltInCaller(address newCaller)" ];
    // iface = new ethers.utils.Interface(ABI);
    // encodedFunctionData = iface.encodeFunctionData(
    //     "changeBuiltInCaller",
    //     [address.cfxMappedEVMSpaceAddress(contractAddress.coreSpaceCrossVmProxy)]
    // )
    //
    // await crossSpaceCall
    //     .callEVM(contractAddress.eSpaceCrossVMProxy, encodedFunctionData)
    //     .sendTransaction({from: defaultAccount.address})
    //     .executed();
    //
    // console.log("Builtin caller changed!!");

    printContractAddress()
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
