// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

interface ICrossVmErc20 {
    function handleDeposit(address receiver, uint256 amount) external;
    function handleWithdraw() external returns (uint256);
    function deposit(bytes20 eSpaceReciever, uint256 amount) external;
    function withdraw(address receiver) external;
}