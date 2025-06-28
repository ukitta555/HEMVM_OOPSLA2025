import { ethers } from "hardhat";

async function main() {
    let [mainAccount] = await ethers.getSigners();

    // let Proxy = await ethers.getContractFactory("CrossVmProxyReverse");
    // const proxy = await Proxy.deploy({gasLimit: 30000000});
    // await proxy.deployed();
    // console.log(`Deploy proxy for reverse demo at ${proxy.address}`);
    let eSpaceCoin = await ethers.getContractAt("ESpaceCoin", "0x471934422642acf5f667370d74bd0732e3911d32");
    console.log ("trying to get balance of a random address without error", await eSpaceCoin.balanceOf("0x14Dcb427A216216791fB63973c5b13878de30916"));


    // let CrossUniswapWrapper = await ethers.getContractFactory("CrossUniswapWrapper");
    // const crossUniswapWrapper = await CrossUniswapWrapper.deploy({gasLimit: 30000000});
    // await crossUniswapWrapper.deployed();

    // console.log(`Deploy Cross Uniswap Proxy at ${crossUniswapWrapper.address}`);
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
