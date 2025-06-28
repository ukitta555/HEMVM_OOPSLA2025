// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../interfaces/ICrossVmErc20Proxy.sol";
import "../interfaces/ICrossVmErc20.sol";
import "../interfaces/ICrossVM.sol";


contract VaultErc20 is ICrossVmErc20 {
    ICrossVM constant crossVM =
        ICrossVM(0x0888000000000000000000000000000000000006);
    ICrossVmErc20Proxy immutable crossVmProxy;
    IERC20 immutable token;
    

    constructor(address token_) {
        crossVmProxy = ICrossVmErc20Proxy(msg.sender);
        token = IERC20(token_);
    }

    function deposit(bytes32 moveReceiver, uint256 amount) public {
        // crossVM.log(abi.encodePacked(token.balanceOf(address(msg.sender))));
        token.transferFrom(msg.sender, address(this), amount);
        crossVmProxy.deposit(moveReceiver, amount);
    }

    function withdraw(address receiver) public {
        uint256 amount = crossVmProxy.withdraw();
        token.transfer(receiver, amount);
    }

    function handleDeposit(address receiver, uint256 amount) public {
        require(msg.sender == address(crossVmProxy), "Forbidden");
        token.transfer(receiver, amount);
    }

    function handleWithdraw() public returns (uint256) {
        require(msg.sender == address(crossVmProxy), "Forbidden");
        uint256 amount = token.balanceOf(address(crossVmProxy));
        token.transferFrom(address(crossVmProxy), address(this), amount);
        return amount;
    }
}