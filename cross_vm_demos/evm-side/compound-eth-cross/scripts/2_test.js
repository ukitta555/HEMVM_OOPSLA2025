const fs = require('fs');
const { network } = require('hardhat');
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
  const [deployer] = await ethers.getSigners();
  const provider = ethers.getDefaultProvider(network.config.url);

  console.log("Account:", deployer.address);

  console.log("Account balance:", (await deployer.getBalance()).toString());


  const MyContract = await ethers.getContractAt("MyContract", contractAddress.MyContract, deployer);
  const CErc20 = await ethers.getContractAt("contracts/CErc20.sol:CErc20", contractAddress.CErc20, deployer);
  const CErc20Twin = await ethers.getContractAt("contracts/CErc20.sol:CErc20", contractAddress.CErc20Twin, deployer);
  console.log(">> Found MyContract at:", MyContract.address);
  console.log(">> Found CErc20 (1) at:", CErc20.address);
  console.log(">> Found CErc20 (2) at:", CErc20Twin.address);
  const EthUnderlying = await ethers.getContractAt("EthCoin", contractAddress.EthCoin, deployer);
  const DMCUnderlying = await ethers.getContractAt("MirrorErc20", contractAddress.DMC, deployer);
  console.log(">> Found DMC at:", DMCUnderlying.address);

  // approve amount to transfer
  console.log("Approve tokens before minting...");
  const amt = ethers.utils.parseEther("1000");
  let tx = await EthUnderlying.approve(CErc20Twin.address, amt);
  await tx.wait();
  console.log(">>> Done");

  console.log("balance of DMC", await EthUnderlying.balanceOf(deployer.address));
  // add liquidity to the market
  // (Vlad) ... <-> supply FaucetToken2 for CFaucetToken2
  console.log(`Supply DMC liquidity to the Compound, amount ${amt}`);
  tx = await CErc20Twin.mint(amt);
  await tx.wait();
  console.log(">> ✅ Done");


  // // check balance
  // let balanceERC20 = await FaucetToken.balanceOf(contractAddress.MyContract);
  // console.log(`MyContract pre-balance of FaucetToken ${balanceERC20}`);
  // let balanceERC20Twin = await FaucetToken2.balanceOf(contractAddress.MyContract);
  // console.log(`MyContract pre-balance of FaucetToken2 ${balanceERC20Twin}`);
  //
  // // lend to MyContract
  // const amt_to_suppply_div1e18 = "0.1";
  // const amt_to_suppply = ethers.utils.parseEther(amt_to_suppply_div1e18);
  // console.log(`Supply ${amt_to_suppply_div1e18} FaucetToken and borrow 0.002 FaucetToken2 ...`);
  // tx = await MyContract.borrowEthExample(
  //   contractAddress.CErc20Twin,
  //   contractAddress.CErc20,
  //   contractAddress.FaucetToken,
  //   amt_to_suppply
  // );
  // await tx.wait();
  // console.log(">> ✅ Done");
  // // check balance
  // balanceERC20 = await FaucetToken.balanceOf(contractAddress.MyContract);
  // console.log(`MyContract post-balance of FaucetToken ${balanceERC20}`);
  // balanceERC20Twin = await FaucetToken2.balanceOf(contractAddress.MyContract);
  // console.log(`MyContract post-balance of FaucetToken2 ${balanceERC20Twin}`);
  // const borrowBalanceStored = await CErc20Twin.borrowBalanceStored(contractAddress.MyContract);
  // console.log(`Current FaucetToken2 borrow amount ${borrowBalanceStored}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });