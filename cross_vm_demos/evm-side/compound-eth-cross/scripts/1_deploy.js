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
  const [deployer] = await ethers.getSigners();

  console.log("Deploying contracts with the account:", deployer.address);
  console.log("Account balance:", (await deployer.getBalance()).toString());

  const MyContract = await ethers.getContractFactory("MyContract");
  const myContract = await MyContract.deploy();
  await myContract.deployed();
  contractAddress.MyContract = myContract.address.toLowerCase();
  console.log(">> ✅ MyContract address:", contractAddress.MyContract);

  contractAddress.EthCoin = "0x63B5dc8063eBB9BA9E05d74EC48B8C570f7624Cc";
  console.log(">> EthCoin address:", contractAddress.EthCoin);
  contractAddress.DMC = "0x5ca0f43868e106ac9aec48f8f1285896c0b9865d";
  console.log(">> DMC address:", contractAddress.DMC);
  printContractAddress();

  await deployCErc20(deployer);
  await deployCErc20Twin(deployer);
  // await deployCEther(deployer);
}

async function deployCErc20(deployer) {
  const CErc20 = await ethers.getContractFactory("contracts/CErc20.sol:CErc20");
  const cErc20 = await CErc20.deploy(
    contractAddress.DMC,
    ethers.utils.parseEther("200000000"),
    `cDMC`,
    `cDMC`,
    18,
    deployer.address,
    {gasLimit: 30000000}
  );
  await cErc20.deployed();
  contractAddress.CErc20 = cErc20.address.toLowerCase();
  console.log(">> ✅ Collateral CErc20 (1) address:", contractAddress.CErc20);
  printContractAddress();
}

async function deployCErc20Twin(deployer) {
  const CErc20 = await ethers.getContractFactory("contracts/CErc20.sol:CErc20");
  const cErc20 = await CErc20.deploy(
    contractAddress.EthCoin,
    ethers.utils.parseEther("200000000"),
    `CETH`,
    `CETH`,
    18,
    deployer.address,
    {gasLimit: 30000000}
  );
  await cErc20.deployed();
  contractAddress.CErc20Twin = cErc20.address.toLowerCase();
  console.log(">> ✅ Borrow CErc20 (2) address:", contractAddress.CErc20Twin);
  printContractAddress();
}
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });