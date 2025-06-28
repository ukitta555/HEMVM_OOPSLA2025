// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import "../interfaces/ICrossVM.sol";
import "../interfaces/ICrossVmErc20.sol";
import "../interfaces/ICrossVmErc20Proxy.sol";
import "./VaultErc20.sol";
import "./MirrorErc20.sol";

struct TokenInfo {
    IERC20 token;
    uint64 evmDecimal;
    uint64 moveDecimal;
    bytes moveType;
    string moveTypeDesc;
}

contract CrossVmProxyERC20 {
    ICrossVM constant crossVM =
        ICrossVM(0x0888000000000000000000000000000000000006);
    address constant ZERO_ADDRESS = 0x0000000000000000000000000000000000000000;
    bytes32 constant handler =
        0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06;

    mapping(address => TokenInfo) private tokenInfo;
    mapping(address => ICrossVmErc20) public tokenToPortal;
    mapping(bytes32 => ICrossVmErc20) public sigToPortal;
    mapping(bytes32 => IERC20Metadata) public sigToToken;


    function knownSender(address sender) public view returns (bool) {
        return
            address(tokenInfo[sender].token) !=
            ZERO_ADDRESS;
    }

    function getTokenInfo(address portal) public view returns (TokenInfo memory){
        return tokenInfo[portal];
    }

    function toMoveAmount(TokenInfo memory info, uint256 amount)
        public
        pure
        returns (uint64)
    {
        if (info.evmDecimal > info.moveDecimal) {
            amount /= 10**(info.evmDecimal - info.moveDecimal);
        } else {
            amount *= 10**(info.moveDecimal - info.evmDecimal);
        }
        require(amount < uint256(type(uint64).max), "Move amount overflow");
        return uint64(amount);
    }

    function toEvmAmount(TokenInfo memory info, uint64 amount_)
        public
        pure
        returns (uint256)
    {
        uint256 amount = uint256(amount_);
        if (info.evmDecimal > info.moveDecimal) {
            amount *= 10**(info.evmDecimal - info.moveDecimal);
        } else {
            amount /= 10**(info.moveDecimal - info.evmDecimal);
        }
        return amount;
    }

    function deposit(bytes32 moveReceiver, uint256 amount) external {
        require(knownSender(msg.sender), "Unknown Sender");
        TokenInfo memory info = tokenInfo[msg.sender];

        bytes[] memory data = new bytes[](2);
        data[0] = crossVM.encodeBytes32(moveReceiver); 
        data[1] = crossVM.encodeU64(toMoveAmount(info, amount));

        bytes[] memory coinType = new bytes[](1);
        coinType[0] = info.moveType;

        crossVM.callMove(handler, "cross_vm_coin_erc20", "deposit", data, coinType);
    }

    function withdraw() external returns (uint256) {
        require(knownSender(msg.sender), "Unknown Sender");
        TokenInfo memory info = tokenInfo[msg.sender];

        bytes[] memory coinType = new bytes[](1);
        coinType[0] = info.moveType;

        bytes memory rawAmount = crossVM.callMove(
            handler,
            "cross_vm_coin_erc20",
            "withdraw",
            new bytes[](0),
            coinType
        );
        return toEvmAmount(info, crossVM.decodeU64(rawAmount));
    }

    function requireBuiltinCaller(string memory caller) view internal {
        require(msg.sender == address(crossVM), "Incorrect invoker");
        require(keccak256(bytes(caller)) == keccak256(bytes("0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06::cross_vm_coin_erc20::CallType")), "Incorrect sender");
    }

    function bytesToAddress(bytes memory data) private pure returns (address addr) {
        require(data.length==20, "Invalid length in decoding address");
        assembly {
            addr := mload(add(data, 20))
        } 
    }


    function handleDeposit(string memory caller, bytes[] memory data) public returns (bytes memory) {
        requireBuiltinCaller(caller);
        address receiver = bytesToAddress(data[0]);
        uint64 moveAmount = crossVM.decodeU64(data[1]);
        bytes32 type_sig = keccak256(data[2]);

        ICrossVmErc20 impl = sigToPortal[type_sig];
        TokenInfo memory info = tokenInfo[address(impl)];

        uint256 evmAmount = toEvmAmount(info, moveAmount);

        impl.handleDeposit(receiver, evmAmount);

        return new bytes(0);
    }

    function handleWithdraw(string memory caller, bytes[] memory data) public returns (bytes memory) {
        requireBuiltinCaller(caller);

        bytes32 type_sig = keccak256(data[0]);
        ICrossVmErc20 impl = sigToPortal[type_sig];
        TokenInfo memory info = tokenInfo[address(impl)];

        uint256 evmAmount = impl.handleWithdraw();
        uint64 moveAmount = toMoveAmount(info, evmAmount);

        return crossVM.encodeU64(moveAmount);
    }

    function _setInfo(ICrossVmErc20 impl, IERC20Metadata token, bytes memory coinType, bytes memory encodedDecimal, bytes memory typeName) public {
        bytes32 type_sig = keccak256(coinType);
        uint64 decimal = crossVM.decodeU64(encodedDecimal);
        string memory moveTypeDesc = string(typeName);

        sigToPortal[type_sig] = impl;
        sigToToken[type_sig] = IERC20Metadata(token);
        tokenToPortal[address(token)] = impl;
        tokenInfo[address(impl)] = TokenInfo({
            token: IERC20(token),
            evmDecimal: uint64(token.decimals()),
            moveDecimal: decimal,
            moveType: coinType,
            moveTypeDesc: moveTypeDesc
        });
        crossVM.log(bytes(moveTypeDesc));
    }

    function handleNewCoin(string memory caller, bytes[] memory data) public returns (bytes memory) {
        requireBuiltinCaller(caller);

        string memory name = string(data[3]);
        string memory symbol = string(data[4]);

        MirrorErc20 mirror = new MirrorErc20(name, symbol);
        IERC20Metadata token = IERC20Metadata(mirror);
        ICrossVmErc20 impl = ICrossVmErc20(mirror);

        crossVM.log("Mirror address");
        crossVM.log(abi.encodePacked(address(mirror)));

        _setInfo(impl, token, data[0], data[1], data[2]);

        return abi.encodePacked(address(token));
    }

    function handleLinkCoin(string memory caller, bytes[] memory data) public returns (bytes memory) {
        requireBuiltinCaller(caller);

        IERC20Metadata token = IERC20Metadata(bytesToAddress(data[3]));
        ICrossVmErc20 impl = ICrossVmErc20(new VaultErc20(address(token)));

        _setInfo(impl, token, data[0], data[1], data[2]);

        crossVM.log("Vault address");
        crossVM.log(abi.encodePacked(address(impl)));

        token.approve(address(impl), type(uint256).max);

        return abi.encodePacked(address(token));
    }

    function queryErc20Name(string memory, bytes[] memory data) public view returns (bytes memory) {
        IERC20Metadata token = IERC20Metadata(bytesToAddress(data[0]));
        return bytes(token.name());
    }

    function queryErc20Symbol(string memory, bytes[] memory data) public view returns (bytes memory) {
        IERC20Metadata token = IERC20Metadata(bytesToAddress(data[0]));
        return bytes(token.symbol());
    }

    // TODO: in experiments, call crossVM.callMove directly -> need to do in both of the versions; for now, use this version everywhere
    function sendETHCrossSpace(bytes32 recepient) public payable {
        // token.approve(address(this), type(uint256).max);
        // token.transfer(address(this), amount);
        // crossVM.log(abi.encodePacked(address(msg.sender).balance));
        // crossVM.callMove{value: 1 ether}(recepient, "cross_vm_coin_erc20", "fake", new bytes[](0), new bytes[](0)); 
        crossVM.callMove{value: 1 ether}(recepient, "", "", new bytes[](0), new bytes[](0)); 
    }

    // fallback() external payable {}

    // receive() external payable {}
}
