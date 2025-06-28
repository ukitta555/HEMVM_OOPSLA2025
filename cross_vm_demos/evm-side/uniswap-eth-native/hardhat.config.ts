import { HardhatUserConfig } from "hardhat/config";
import '@typechain/hardhat';
import '@nomiclabs/hardhat-waffle';
require("@nomiclabs/hardhat-waffle");

const config: HardhatUserConfig = {
  solidity: {
    compilers: [
      {
        version: '0.5.16',
        settings: {
          optimizer: {
            enabled: true,
            runs: 200,
          },
        },
      },
      {
        version: '0.6.6',
        settings: {
          optimizer: {
            enabled: true,
            runs: 200,
          },
        },
      },
    ],
  },
  defaultNetwork: "localhost",
  networks: {
    localhost: { url:"http://127.0.0.1:8545/", accounts: ["fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa"] }
  }
};

export default config;
