import { Wallet } from "ethers";
import { ethers } from "hardhat";
import { ICrossVM } from "../typechain-types";

function newSigner(): Wallet {
    return new ethers.Wallet("fafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafa", ethers.provider)
}

async function getCrossVmContract(): Promise<ICrossVM> {
    const signer = newSigner();
    return await ethers.getContractAt("ICrossVM", "0x0888000000000000000000000000000000000006", signer);
}

export  {
    newSigner,
    getCrossVmContract
}