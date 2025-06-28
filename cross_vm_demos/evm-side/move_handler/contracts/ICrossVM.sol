// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

interface ICrossVM {
    function callMove(bytes32 addr, string calldata module, string calldata func, bytes calldata data) external payable returns (bytes memory);
    function log(bytes memory data) external;
}