// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

import "./ICrossVM.sol";

contract MoveHandler {
     ICrossVM public constant crossVM  = ICrossVM(0x0888000000000000000000000000000000000006);

    function handleMoveCall(string memory caller, bytes[] memory data) public returns (bytes memory) {
        require(msg.sender == address(crossVM), "Incorrect invoker");
        require(keccak256(bytes(caller)) == keccak256(bytes("0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06::caller::CallType")), "Incorrect sender");

        crossVM.log(data[0]);
        return bytes("I'm Move handler");
    }
}