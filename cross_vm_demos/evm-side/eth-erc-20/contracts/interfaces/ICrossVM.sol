// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

interface ICrossVM {

    function callMove(bytes32 addr, string calldata module, string calldata func, bytes[] calldata data, bytes[] calldata types) external payable returns (bytes memory);

    function log(bytes calldata data) external;

    function encodeU64(uint64 value) external view returns (bytes memory);

    function encodeBytes32(bytes32 value) external view returns (bytes memory);

    function decodeU64(bytes calldata raw) external view returns (uint64);

    function decodeBytes32(bytes calldata raw) external view returns (bytes32);
}