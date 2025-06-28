import {constants, utils} from "ethers";
import {ethers} from "hardhat";
async function main() {
  const [owner] = await ethers.getSigners();
  // console.log(owner)
  const Factory = await ethers.getContractFactory("UniswapV2Factory", owner);
  const factory = await Factory.deploy(owner.address, {gasLimit: 30000000});
  // console.log(factory.interface)
  const factoryAddress = await factory.address;
  console.log('factory', factoryAddress)

  const Token = await ethers.getContractFactory("Token", owner);
  const testCoin1 = await Token.deploy("test1", "T1", {gasLimit: 30000000});
  // await testCoin1.waitForDeployment();
  const testCoin2 = await Token.deploy("test2", "T2", {gasLimit: 30000000});
  // await testCoin2.waitForDeployment();

  const testCoin1Address = testCoin1.address;
  const testCoin2Address = testCoin2.address;
  console.log('test coin 1 address', testCoin1Address)
  console.log('test coin 2 address', testCoin2Address)

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

  const pair = await ethers.getContractAt("UniswapV2Pair", pairAddress, owner);
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

  const approval1 = await testCoin1.approve(routerAddress, constants.MaxUint256, {gasLimit: 30000000});
  await approval1.wait();
  const approval2 = await testCoin2.approve(routerAddress, constants.MaxUint256, {gasLimit: 30000000});
  await approval2.wait();

  const token0Amount = utils.parseUnits("100");
  const token1Amount = utils.parseUnits("100");
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

  reserves = await pair.getReserves();
  console.log("reserves", reserves);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});