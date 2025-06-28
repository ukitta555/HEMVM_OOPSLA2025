// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

interface ICrossVM {
    event Call(bytes20 indexed sender, bytes20 indexed receiver, uint256 value, uint256 nonce, bytes data);

    event Create(bytes20 indexed sender, bytes20 indexed contract_address, uint256 value, uint256 nonce, bytes init);

    event Withdraw(bytes20 indexed sender, address indexed receiver, uint256 value, uint256 nonce);

    event Outcome(bool success);

    /**
     * @dev Deploy a contract in eSpace
     * @param init bytes -  The contract init bytecode
     * @return bytes20 - The hex address of the deployed contract
     */
    function createEVM(bytes calldata init) external payable returns (bytes20);

    /**
     * @dev Transfer CFX from Core space to eSpace specify address. Transfer amount is specified by transaction value.
     * @param to bytes20 - The hex address of the receiver address in eSpace
     * @return output bytes
     */
    function transferEVM(bytes20 to) external payable returns (bytes memory output);

    /**
     * @dev Call eSpace contract method from Core space
     * @param to bytes20 - The hex address of the contract in eSpace
     * @param data bytes - The contract method call data
     * @return output bytes - Method call result
     */
    function callEVM(bytes20 to, bytes calldata data) external payable returns (bytes memory output);

    /**
     * @dev Static call eSpace contract method from Core space
     * @param to bytes20 - The hex address of the contract in eSpace
     * @param data bytes - The contract method call data
     * @return output bytes - Method call result
     */
    function staticCallEVM(bytes20 to, bytes calldata data) external view returns (bytes memory output);

    /**
     * @dev Widthdraw CFX from eSpace mapped account's balance
     * @param value uint256 - The amount of CFX to be withdrawn
     */
    function withdrawFromMapped(uint256 value) external;

    /**
     * @dev Query eSpace mapped account's CFX balance
     * @param addr address - The core address to query
     * @return uint256 - Balance
     */
    function mappedBalance(address addr) external view returns (uint256);

    /**
     * @dev Query eSpace mapped account's nonce
     * @param addr address - The core address to query
     * @return uint256 - Balance
     * */
    function mappedNonce(address addr) external view returns (uint256);

    function log(bytes calldata data) external;
}