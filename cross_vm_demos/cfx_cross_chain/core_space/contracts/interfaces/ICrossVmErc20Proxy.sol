// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

interface ICrossVmErc20Proxy {
    function deposit(bytes20 eSpaceReceiver, uint256 amount) external;
    function withdraw() external returns (uint256);
}
