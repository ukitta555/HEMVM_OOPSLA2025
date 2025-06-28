// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;


import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "../interfaces/ICrossVmErc20Proxy.sol";
import "../interfaces/ICrossVmErc20.sol";

contract MirrorErc20 is ERC20, ICrossVmErc20 {
    address constant cashierAddress = 0xcAcacaCacacACaCACaCaCACAcacAcaCACacAcAcA;
    ICrossVmErc20Proxy immutable crossVmProxy;
    

    constructor(string memory name_, string memory symbol_) ERC20(name_, symbol_){
        crossVmProxy = ICrossVmErc20Proxy(msg.sender);
    }

    function deposit(bytes32 moveReceiver, uint256 amount) public {
        _burn(msg.sender, amount);
        crossVmProxy.deposit(moveReceiver, amount);
    }

    function withdraw(address receiver) public {
        uint256 amount = crossVmProxy.withdraw();
        _mint(receiver, amount);
    }

    function handleDeposit(address receiver, uint256 amount) public {
        require(msg.sender == address(crossVmProxy), "Forbidden");
        _mint(receiver, amount);
    }

    function handleWithdraw() public returns (uint256) {
        require(msg.sender == address(crossVmProxy), "Forbidden");
        uint256 amount = balanceOf(address(crossVmProxy));
        _burn(address(crossVmProxy), amount);
        return amount;
    }
}