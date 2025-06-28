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


async function main() {
  const [deployer] = await ethers.getSigners();
  const provider = ethers.getDefaultProvider(network.config.url);

  console.log("Account:", deployer.address);

  console.log("Account balance:", (await deployer.getBalance()).toString());

  
  const MyContract = await ethers.getContractAt("MyContract", contractAddress.MyContract, deployer);
  const CErc20 = await ethers.getContractAt("contracts/CErc20.sol:CErc20", contractAddress.CErc20, deployer);
  console.log(">> Found CErc20 at:", CErc20.address);
  const CErc20Twin = await ethers.getContractAt("contracts/CErc20.sol:CErc20", contractAddress.CErc20Twin, deployer);
  console.log(">> Found CErc20Twin at:", CErc20Twin.address);
  const FaucetToken = await ethers.getContractAt("FaucetToken", contractAddress.FaucetToken, deployer);
  const FaucetToken2 = await ethers.getContractAt("FaucetToken", contractAddress.FaucetToken2, deployer);


  // check balance
  let balanceERC20 = await FaucetToken.balanceOf(contractAddress.MyContract);
  console.log(`MyContract pre-balance of FaucetToken ${balanceERC20}`);
  let balanceERC20Twin = await FaucetToken2.balanceOf(contractAddress.MyContract);
  console.log(`MyContract pre-balance of FaucetToken2 ${balanceERC20Twin}`);

  let borrowBalanceStored = await CErc20Twin.borrowBalanceStored(contractAddress.MyContract);

  // repay from MyContract
  console.log(`Repay ${borrowBalanceStored} FaucetToken2 to CFaucetToken2 (a.k.a. CERC20Twin) ...`);
  tx = await MyContract.myEthRepayBorrow(
      contractAddress.CErc20Twin,
      contractAddress.CErc20,
      FaucetToken2.address,
      borrowBalanceStored,
      {gasLimit: 30000000},
  );
  await tx.wait();
  console.log(">> ✅ Done");
  // check balance
  balanceERC20 = await FaucetToken.balanceOf(contractAddress.MyContract);
  console.log(`MyContract post-balance of FaucetToken ${balanceERC20}`);
  balanceERC20Twin = await FaucetToken2.balanceOf(contractAddress.MyContract);
  console.log(`MyContract post-balance of FaucetToken2 ${balanceERC20Twin}`);
  borrowBalanceStored = await CErc20Twin.borrowBalanceStored(contractAddress.MyContract);
  console.log(`Current ETH borrow amount ${borrowBalanceStored}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });