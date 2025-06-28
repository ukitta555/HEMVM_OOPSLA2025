import {utils} from "ethers";
import {ethers} from "hardhat";

async function main() {
  const [owner] = await ethers.getSigners();
  console.log("owner address", owner.address)
  const Factory = await ethers.getContractFactory("UniswapV2Factory", owner);
  const factory = await Factory.deploy(owner.address, {gasLimit: 30000000});
  // console.log(factory.interface)
  const factoryAddress = await factory.address;
  console.log('factory', factoryAddress)

  const testCoin1 = await ethers.getContractAt("EthCoin", "0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc", owner);
  const testCoin2 = await ethers.getContractAt("MirrorErc20", "0x5ca0f43868e106ac9aec48f8f1285896c0b9865d", owner);
  // const Token = await ethers.getContractFactory("Token", owner);
  // const testCoin3 = await Token.deploy("test1", "T1", {gasLimit: 30000000});
  // const testCoin4 = await Token.deploy("test2", "T2", {gasLimit: 30000000});

  const testCoin1Address = testCoin1.address;
  const testCoin2Address = testCoin2.address;
  // const testCoin3Address = testCoin3.address;
  // const testCoin4Address = testCoin4.address;
  console.log('test coin 1 address', testCoin1Address)
  console.log('test coin 2 address', testCoin2Address)
  // console.log('test coin 3 address', testCoin3Address)
  // console.log('test coin 4 address', testCoin4Address)


  // await testCoin1.connect(owner).mint(
  //     owner.address,
  //     utils.parseUnits('100000')
  // );
  // console.log("mint1")
  // await testCoin2.connect(owner).mint(
  //     owner.address,
  //     utils.parseUnits('100000')
  // );
  // console.log("mint2")

  try {
    const tx1 = await factory.createPair(testCoin1Address, testCoin2Address, {gasLimit: 30000000});
    await tx1.wait();
    console.log("factory create pair")
  } catch(e) {
    console.log("Error!");
    process.exit(1);
  }
  const pairAddress = await factory.getPair(testCoin1Address, testCoin2Address);
  console.log("address of the pair", pairAddress)

  let pair = await ethers.getContractAt("UniswapV2Pair", pairAddress, owner);
  let reserves = await pair.getReserves();
  console.log("reserves", reserves)

  const WETH = await ethers.getContractFactory("WETH", owner);
  const weth = await WETH.deploy({gasLimit: 30000000})
  const wethAddress = weth.address;
  console.log("weth ", wethAddress);

  const Router = await ethers.getContractFactory("UniswapV2Router02", owner);
  const router = await Router.deploy(factoryAddress, wethAddress, {gasLimit: 30000000});
  const routerAddress = router.address;
  console.log("router ", routerAddress);

  const approval1 = await testCoin1.approve(routerAddress, utils.parseUnits("1000"), {gasLimit: 30000000});
  await approval1.wait();
  const approval2 = await testCoin2.approve(routerAddress, utils.parseUnits("1000"), {gasLimit: 30000000});
  await approval2.wait();
  // const approval3 = await testCoin3.approve(routerAddress, utils.parseUnits("1000"), {gasLimit: 30000000});
  // await approval3.wait();
  // const approval4 = await testCoin4.approve(routerAddress, utils.parseUnits("1000"), {gasLimit: 30000000});
  // await approval4.wait();
  console.log("approved")

  const token0Amount = utils.parseUnits("10");
  const token1Amount = utils.parseUnits("10");
  console.log("Amounts to add as liquidity: ", token0Amount.toString(), token1Amount.toString())
  console.log ("Decimals: ", await testCoin1.decimals(), await testCoin2.decimals());
  const deadline = Math.floor((Date.now() / 1000) + (100 * 60));

  const addLiquidityTx = await router.connect(owner)
      .addLiquidity(
        testCoin1Address,
        testCoin2Address,
        token0Amount,
        token1Amount,
        1,
        1,
        owner.address,
        deadline,
        { gasLimit: 30000000 }
    )
  await addLiquidityTx.wait();
  console.log("liquidity added");

  reserves = await pair.getReserves();
  console.log("reserves", reserves);
  const liquidityTokens = await pair.balanceOf(owner.address, {gasLimit: 300000000});
  console.log("LP tokens owned after adding liquidity", liquidityTokens);
}



main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

