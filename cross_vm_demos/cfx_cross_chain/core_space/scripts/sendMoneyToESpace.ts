import {conflux} from "hardhat";
import {address, Conflux, Contract, Drip, PrivateKeyAccount} from "js-conflux-sdk";

async function main() {
    // let Proxy = await hre.conflux.getContractFactory("CrossVmProxy");
    // const proxy = await Proxy.deploy({gasLimit: 30000000});
    // await proxy.deployed();

    // console.log(`Deploy proxy at ${proxy.address}`);
    const signers: PrivateKeyAccount[] = await conflux.getSigners();
    const defaultAccount = signers[0];

    console.log("Mapped address:", address.cfxMappedEVMSpaceAddress(defaultAccount.address));

    const crossSpaceCall = conflux.InternalContract("CrossSpaceCall");

    const result = await crossSpaceCall
        .transferEVM(address.cfxMappedEVMSpaceAddress(defaultAccount.address)) // same private key, espace address
        .sendTransaction({
            from: defaultAccount.address,
            value: Drip.fromCFX(500)
        })
        .executed();


    console.log(`Sent 500 CFX to the ${address.cfxMappedEVMSpaceAddress(defaultAccount.address)} address`);
    // let SwapRouter = aewait ethers.getContractFactory("MoveSwapRouter");
    // const router = await SwapRouter.deploy(proxy.address, {gasLimit: 30000000})
    // await router.deployed();
    //
    // console.log(`Deploy swap at ${router.address}`);
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
