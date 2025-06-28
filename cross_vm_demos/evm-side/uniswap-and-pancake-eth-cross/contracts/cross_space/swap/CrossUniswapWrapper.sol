// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import "../interfaces/ICrossVM.sol";
import "../coin/CrossVmProxyReverse.sol";
import "../../periphery/interfaces/IUniswapV2Router02.sol";

contract CrossUniswapWrapper {
    ICrossVM constant crossVM =
        ICrossVM(0x0888000000000000000000000000000000000006);
    CrossVmProxyReverse crossVmProxy =
       CrossVmProxyReverse(0xcC166f312524Cc88E2c16c3bdd5735a23376B1fb);
    IUniswapV2Router02 uniswap = IUniswapV2Router02(0xa9B54DA9D0D2DbfB29d512d6babaA7D0f87E6959);
    bytes32 constant handler =
        0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06;


    struct AddLiquidityArgs {
        bytes rawTypeA;
        bytes rawTypeB;
        bytes rawTypeLPToken;
        uint256 amountA;
        uint256 amountB;
        uint256 amountMinA;
        uint256 amountMinB;
        uint64 deadline;
    }

    struct RemoveLiquidityArgs {
        bytes rawTypeA;
        bytes rawTypeB;
        bytes rawTypeLPToken;
        uint256 amountLPToken;
        uint256 amountMinA;
        uint256 amountMinB;
        uint64 deadline;
    }

    struct SwapExactTokensArgs {
        bytes rawTypeA;
        bytes rawTypeB;
        uint256 amountInA;
        uint256 amountOutMinB;
        uint64 deadline;
    }

    modifier builtinCallerGuard(string memory caller) {
        require(msg.sender == address(crossVM), "Incorrect invoker");
        require(keccak256(bytes(caller)) == keccak256(bytes("0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06::cross_vm_coin_reverse_demo::CallType")), "Incorrect sender");
        _;
    }

    function handleAddLiquidity(string memory caller, bytes[] memory data) builtinCallerGuard(caller) public returns (bytes memory) {
        crossVM.log("Call made to adding liquidity!");
        AddLiquidityArgs memory args;
        args.rawTypeA = data[0];
        args.rawTypeB = data[1];
        args.rawTypeLPToken = data[2];

        IERC20Metadata tokenA = crossVmProxy.sigToToken(keccak256(args.rawTypeA));
        crossVM.log(abi.encodePacked(address(tokenA)));

        IERC20Metadata tokenB = crossVmProxy.sigToToken(keccak256(args.rawTypeB));
        crossVM.log(abi.encodePacked(address(tokenB)));

        IERC20Metadata LPToken = crossVmProxy.sigToToken(keccak256(args.rawTypeLPToken));
        crossVM.log(abi.encodePacked(address(LPToken)));

        tokenA.approve(address(uniswap), type(uint256).max);
        tokenB.approve(address(uniswap), type(uint256).max);

        TokenInfo memory infoA = crossVmProxy.getTokenInfo(address(crossVmProxy.tokenToPortal(address(tokenA))));
        TokenInfo memory infoB = crossVmProxy.getTokenInfo(address(crossVmProxy.tokenToPortal(address(tokenB))));
        args.amountA = toEvmAmount(infoA, crossVM.decodeU64(data[3]));
        args.amountB = toEvmAmount(infoB, crossVM.decodeU64(data[4]));
        args.amountMinA = toEvmAmount(infoA, crossVM.decodeU64(data[5]));
        args.amountMinB = toEvmAmount(infoB, crossVM.decodeU64(data[6]));
        args.deadline = crossVM.decodeU64(data[7]);

        uniswap.addLiquidity(
                address(tokenA),
                address(tokenB),
                args.amountA,
                args.amountB,
                args.amountMinA,
                args.amountMinB,
                address(crossVmProxy),
                args.deadline
        );
        crossVM.log("After addLiquidity");
        return new bytes(0);
    }

    function handleRemoveLiquidity(string memory caller, bytes[] memory data) builtinCallerGuard(caller) public returns (bytes memory) {
        crossVM.log("Call made to removing liquidity!");
        RemoveLiquidityArgs memory args;
        args.rawTypeA = data[0];
        args.rawTypeB = data[1];
        args.rawTypeLPToken = data[2];

        IERC20Metadata tokenA = crossVmProxy.sigToToken(keccak256(args.rawTypeA));
        crossVM.log(abi.encodePacked(address(tokenA)));

        IERC20Metadata tokenB = crossVmProxy.sigToToken(keccak256(args.rawTypeB));
        crossVM.log(abi.encodePacked(address(tokenB)));

        IERC20Metadata LPToken = crossVmProxy.sigToToken(keccak256(args.rawTypeLPToken));
        crossVM.log(abi.encodePacked(address(LPToken)));

        TokenInfo memory infoA = crossVmProxy.getTokenInfo(address(crossVmProxy.tokenToPortal(address(tokenA))));
        TokenInfo memory infoB = crossVmProxy.getTokenInfo(address(crossVmProxy.tokenToPortal(address(tokenB))));
        TokenInfo memory infoLP = crossVmProxy.getTokenInfo(address(crossVmProxy.tokenToPortal(address(LPToken))));

        args.amountLPToken = toEvmAmount(infoLP, crossVM.decodeU64(data[3]));
        args.amountMinA = toEvmAmount(infoA, crossVM.decodeU64(data[4]));
        args.amountMinB = toEvmAmount(infoB, crossVM.decodeU64(data[5]));
        args.deadline = crossVM.decodeU64(data[6]);

        LPToken.approve(address(uniswap), type(uint256).max);

        uniswap.removeLiquidity(
            address(tokenA),
            address(tokenB),
            args.amountLPToken,
            args.amountMinA,
            args.amountMinB,
            address(crossVmProxy),
            args.deadline
        );
        crossVM.log("After removeLiquidity");

        return new bytes(0);
    }

    function handleSwapExactTokensForTokens(string memory caller, bytes[] memory data) builtinCallerGuard(caller) public returns (bytes memory) {
        crossVM.log("Call made to swapExact!");
        SwapExactTokensArgs memory args;
        args.rawTypeA = data[0];
        args.rawTypeB = data[1];

        IERC20Metadata tokenA = crossVmProxy.sigToToken(keccak256(args.rawTypeA));
//        crossVM.log(abi.encodePacked(address(tokenA)));

        IERC20Metadata tokenB = crossVmProxy.sigToToken(keccak256(args.rawTypeB));
//        crossVM.log(abi.encodePacked(address(tokenB)));

        TokenInfo memory infoA = crossVmProxy.getTokenInfo(address(crossVmProxy.tokenToPortal(address(tokenA))));
        TokenInfo memory infoB = crossVmProxy.getTokenInfo(address(crossVmProxy.tokenToPortal(address(tokenB))));

        args.amountInA = toEvmAmount(infoA, crossVM.decodeU64(data[2]));
        args.amountOutMinB = toEvmAmount(infoB, crossVM.decodeU64(data[3]));
        args.deadline = crossVM.decodeU64(data[4]);

        tokenA.approve(address(uniswap), type(uint256).max);
        tokenB.approve(address(uniswap), type(uint256).max);

        tokenA.approve(address(uniswap), type(uint256).max);
        tokenB.approve(address(uniswap), type(uint256).max);

        address[] memory path = new address[](2);
        path[0] = address(tokenA);
        path[1] = address(tokenB);

        uniswap.swapExactTokensForTokens(
            args.amountInA,
            args.amountOutMinB,
            path,
            address(crossVmProxy),
            args.deadline
        );

        return new bytes(0);
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

    function stringToBytes(string memory s) public pure returns (bytes memory){
        bytes memory b3 = bytes(s);
        return b3;
    }
}
