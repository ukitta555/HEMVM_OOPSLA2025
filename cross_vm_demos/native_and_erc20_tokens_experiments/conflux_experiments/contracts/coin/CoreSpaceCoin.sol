// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";


contract CoreSpaceCoin is ERC20, Ownable {
    constructor() ERC20("Core Space Coin", "CORECOIN") {}

    function mint(address account, uint256 amount) onlyOwner external{
        _mint(account, amount);
    }
}