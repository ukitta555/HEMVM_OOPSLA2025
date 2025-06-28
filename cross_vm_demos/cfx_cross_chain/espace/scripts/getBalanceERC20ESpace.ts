import { ethers } from "hardhat";


const fs = require('fs');

// contract addresses
let contractAddress;

try {
    contractAddress = require(__dirname +
        `/../../core_space/contractAddress.json`);
} catch (e) {
    contractAddress = {};
}
function printContractAddress() {
    fs.writeFileSync(
        __dirname + `/../../core_space/contractAddress.json`,
        JSON.stringify(contractAddress, null, '\t'),
    );
}
async function main() {
    let eSpaceCoin = await ethers.getContractAt("MirrorErc20", contractAddress.eSpaceMirrorAddress);
    console.log (
        "Balance of mirrored CoreSpaceCoin for mapped account:",
        await eSpaceCoin.balanceOf(contractAddress.eSpaceMappedAddress)
    );
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
