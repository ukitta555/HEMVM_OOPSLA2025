// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "../interfaces/ICrossVM.sol";
import "../interfaces/ICrossVmErc20.sol";
import "../interfaces/ICrossVmErc20Proxy.sol";
import "./VaultErc20.sol";
import "./MirrorErc20.sol";


// General agreement: bytes20 = address from another space, address = address from current space
contract CrossVmProxyCFX is Ownable {
    ICrossVM constant crossVM =
        ICrossVM(0x0888000000000000000000000000000000000006);
    address constant ZERO_ADDRESS = 0x0000000000000000000000000000000000000000;
    bytes20 handler = bytes20(0);
    address builtInCaller = address(0);

    mapping(address => IERC20) private portalToToken;
    mapping(address => ICrossVmErc20) public tokenToPortal;
    mapping(bytes20 => ICrossVmErc20) public tokenFromOtherSpaceToPortal;
    mapping(bytes20 => IERC20Metadata) public tokenFromOtherSpaceToToken;

    function requireBuiltinCaller(address caller) view internal {
        require(keccak256(abi.encodePacked(caller)) == keccak256(abi.encodePacked(builtInCaller)), "Incorrect sender");
    }

    function changeHandler(bytes20 newHandler) external onlyOwner {
        handler = newHandler;
    }

    function changeBuiltInCaller(bytes20 newCaller) external onlyOwner {
        builtInCaller = address(newCaller);
    }


    function bytesToAddress(bytes memory data) private pure returns (address addr) {
        require(data.length==20, "Invalid length in decoding address");
        assembly {
            addr := mload(add(data, 20))
        }
    }

    function knownSender(address sender) public view returns (bool) {
        return
            address(portalToToken[sender]) != ZERO_ADDRESS;
    }

    function getTokenInfo(address portal) public view returns (IERC20) {
        return portalToToken[portal];
    }


    function deposit(bytes20 eSpaceReceiver, uint256 amount) external {
        require(knownSender(msg.sender), "Unknown Sender");
        bytes memory payload = abi.encodeWithSignature(
            "handleDeposit(address,uint256,bytes20)",
            address(eSpaceReceiver),
            amount,
            bytes20(address(portalToToken[msg.sender]))
        );

        crossVM.callEVM(handler, payload);
    }

    // Vlad: Conflux has some weird shenanigans for msg.sender in eSpace... (mapped address + large zero padding)
    // can't use callEVM to re-set the built-in caller, simulation fails no matter how I try
    // don't have the time right now to dig in the code to understand why is msg.sender > 42 chars after fetching callEVM result
    // todo: fix access control for eSpace handlers
    function handleDeposit(address receiver, uint256 amount, bytes20 coreAddress) public onlyOwner returns (bytes memory) {
//        requireBuiltinCaller(msg.sender);
        ICrossVmErc20 impl = tokenFromOtherSpaceToPortal[coreAddress];
        impl.handleDeposit(receiver, amount);
        return new bytes(0);
    }

    function withdraw() external  returns (uint256) {
        require(knownSender(msg.sender), "Unknown Sender");
        bytes memory payload = abi.encodeWithSignature(
            "handleWithdraw(bytes20)",
            bytes20(address(portalToToken[msg.sender]))
        );
        return uint256(bytes32(crossVM.callEVM(handler, payload)));
    }

    function handleWithdraw(bytes20 coreAddress) public onlyOwner returns (uint256) {
//        requireBuiltinCaller(msg.sender);
        ICrossVmErc20 impl = tokenFromOtherSpaceToPortal[coreAddress];
        uint256 evmAmount = impl.handleWithdraw();
        return evmAmount;
    }

    function generateVaultAndMirrorForToken(address vaultTokenAddress) public onlyOwner returns  (bytes20) {

        crossVM.log("Generating vault and mirror tokens...");

        IERC20Metadata token = IERC20Metadata(vaultTokenAddress);

        crossVM.log(abi.encodePacked(address(token)));

        ICrossVmErc20 impl = ICrossVmErc20(new VaultErc20(address(token)));

        crossVM.log(abi.encodePacked(address(impl)));

        bytes memory transferPayload = abi.encodeWithSignature(
            "createMirrorCoin(string,string,bytes20)",
            token.name(),
            token.symbol(),
            bytes20(vaultTokenAddress)
        );

        bytes memory result = crossVM.callEVM(handler, transferPayload);
        crossVM.log(result);
        bytes20 mirrorTokenAddress = bytes20(result);

        _setInfo(impl, token, mirrorTokenAddress);
        token.approve(address(impl), type(uint256).max);

        return mirrorTokenAddress;
    }

    function createMirrorCoin(string memory name, string memory symbol, bytes20 vaultTokenAddress) public returns (bytes20) {
//        requireBuiltinCaller(msg.sender);
        MirrorErc20 mirror = new MirrorErc20(name, symbol);
        IERC20Metadata token = IERC20Metadata(mirror);
        ICrossVmErc20 impl = ICrossVmErc20(mirror);

        _setInfo(impl, token, vaultTokenAddress);
        token.approve(address(impl), type(uint256).max);

        return bytes20(address(mirror));
    }

    function _setInfo(ICrossVmErc20 impl, IERC20Metadata token, bytes20 tokenFromOtherSpace) public {
        tokenFromOtherSpaceToPortal[tokenFromOtherSpace] = impl;
        tokenFromOtherSpaceToToken[tokenFromOtherSpace] = IERC20Metadata(token);
        tokenToPortal[address(token)] = impl;
        portalToToken[address(impl)] = IERC20(token);
    }
}
