// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

interface ICrossVmErc20 {
    function handleDeposit(address receiver, uint256 amount) external;
    function handleWithdraw() external returns (uint256);
    function deposit(bytes32 moveReceiver, uint256 amount) external;
    function withdraw(address receiver) external;
}