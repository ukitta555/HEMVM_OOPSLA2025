import { ethers } from "hardhat";

async function main() {
    let [mainAccount] = await ethers.getSigners();

    // let Proxy = await ethers.getContractFactory("CrossVmProxyReverse");
    // const proxy = await Proxy.deploy({gasLimit: 30000000});
    // await proxy.deployed();
    // console.log(`Deploy proxy for reverse demo at ${proxy.address}`);
    try {
        let ESpaceCoin = await ethers.getContractFactory("ESpaceCoin");
        const ecoin = await ESpaceCoin.deploy({gasLimit: 300000, from: "0xF2D76a4a43C7949a09d6CB90d66191a0B4cdFb9F"});
        await ecoin.deployed();
        console.log(`Deploy coin at ${ecoin.address}`);
        await ecoin.mint(mainAccount.address, 10000 * 10 ** 18); // 10000 eCoins
        console.log(`Minted 10000 eCoins to address ${mainAccount}`);

    } catch (e) {
        console.log(e.data)
    }


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
