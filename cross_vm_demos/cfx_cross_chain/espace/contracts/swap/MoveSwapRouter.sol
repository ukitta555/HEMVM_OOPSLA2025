// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

import "../coin/CrossVmProxy.sol";
import "../interfaces/ICrossVmErc20.sol";
import "../interfaces/ICrossVM.sol";

struct SwapPool {
    address tokenX;
    address tokenY;
}

contract MoveSwapRouter {
    CrossVmProxy immutable proxy;
    bytes32 constant handler =
        0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06;
    bytes32 constant cashier =
        0x9bbe73b634c517e145bb101d20302a3558048e7104340fa7f71220674d8ae706;
    ICrossVM constant crossVM =
        ICrossVM(0x0888000000000000000000000000000000000006);

    mapping(bytes32 => address) public lpTokenPool;
    mapping(address => SwapPool) public lpTokenToTokens;

    constructor(address _proxy) {
        proxy = CrossVmProxy(_proxy);
    }

    function approvePortal(address token) public {
        ICrossVmErc20 protal = proxy.tokenToPortal(token);
        IERC20(token).approve(address(protal), type(uint256).max);
    }

    function _swap(
        IERC20Metadata tokenIn,
        IERC20Metadata tokenOut,
        uint amountIn,
        uint amountOut,
        bool exactIn
    ) internal {
        ICrossVmErc20 protalIn = proxy.tokenToPortal(address(tokenIn));
        ICrossVmErc20 protalOut = proxy.tokenToPortal(address(tokenOut));

        TokenInfo memory tokenInfoIn = proxy.getTokenInfo(address(protalIn));
        TokenInfo memory tokenInfoOut = proxy.getTokenInfo(address(protalOut));

        uint64 moveAmountIn = proxy.toMoveAmount(tokenInfoIn, amountIn);
        uint64 moveAmountOut = proxy.toMoveAmount(tokenInfoOut, amountOut);

        tokenIn.transferFrom(msg.sender, address(this), amountIn);
        protalIn.deposit(cashier, amountIn);

        bytes[] memory data = new bytes[](2);
        data[0] = crossVM.encodeU64(moveAmountIn);
        data[1] = crossVM.encodeU64(moveAmountOut);

        bytes[] memory coins = new bytes[](2);
        coins[0] = tokenInfoIn.moveType;
        coins[1] = tokenInfoOut.moveType;

        string memory func;
        if (exactIn) {
            func = "swap_exact_input";
        } else {
            func = "swap_exact_output";
        }

        crossVM.callMove(handler, "swap", func, data, coins);

        if (!exactIn) {
            protalIn.withdraw(msg.sender);
        }
        protalOut.withdraw(msg.sender);
    }

    function swapExactTokensForTokens(
        IERC20Metadata tokenIn,
        IERC20Metadata tokenOut,
        uint amountIn,
        uint amountOutMin
    ) external {
        _swap(
            IERC20Metadata(tokenIn),
            IERC20Metadata(tokenOut),
            amountIn,
            amountOutMin,
            true
        );
    }

    function swapTokensForExactTokens(
        IERC20Metadata tokenIn,
        IERC20Metadata tokenOut,
        uint amountOut,
        uint amountInMax
    ) external {
        _swap(
            IERC20Metadata(tokenIn),
            IERC20Metadata(tokenOut),
            amountInMax,
            amountOut,
            false
        );
    }

    function removeLiquidity(address tokenLP, uint amount) external {
        SwapPool memory pool = lpTokenToTokens[tokenLP];

        ICrossVmErc20 protalX = proxy.tokenToPortal(pool.tokenX);
        ICrossVmErc20 protalY = proxy.tokenToPortal(pool.tokenY);
        ICrossVmErc20 protalLp = proxy.tokenToPortal(tokenLP);

        IERC20(tokenLP).transferFrom(msg.sender, address(this), amount);
        protalLp.deposit(cashier, amount);

        bytes[] memory data;
        bytes[] memory coins;

        {
            TokenInfo memory tokenInfoX = proxy.getTokenInfo(address(protalX));
            TokenInfo memory tokenInfoY = proxy.getTokenInfo(address(protalY));

            data = new bytes[](0);

            coins = new bytes[](2);
            coins[0] = tokenInfoX.moveType;
            coins[1] = tokenInfoY.moveType;
        }

        crossVM.callMove(handler, "swap", "remove_liquidity", data, coins);

        protalX.withdraw(msg.sender);
        protalY.withdraw(msg.sender);
    }

    function addLiquidity(
        IERC20Metadata tokenX,
        IERC20Metadata tokenY,
        uint amountX,
        uint amountY,
        uint amountXmin,
        uint amountYmin
    ) external {
        address lpToken = getLpToken(address(tokenX), address(tokenY));
        ICrossVmErc20 protalX = proxy.tokenToPortal(address(tokenX));
        ICrossVmErc20 protalY = proxy.tokenToPortal(address(tokenY));
        ICrossVmErc20 protalLp = proxy.tokenToPortal(lpToken);

        tokenX.transferFrom(msg.sender, address(this), amountX);
        protalX.deposit(cashier, amountX);
        tokenY.transferFrom(msg.sender, address(this), amountY);
        protalY.deposit(cashier, amountY);

        bytes[] memory data;
        bytes[] memory coins;

        {
            TokenInfo memory tokenInfoX = proxy.getTokenInfo(address(protalX));
            TokenInfo memory tokenInfoY = proxy.getTokenInfo(address(protalY));

            uint64 moveAmountX = proxy.toMoveAmount(tokenInfoX, amountX);
            uint64 moveAmountY = proxy.toMoveAmount(tokenInfoY, amountY);
            uint64 moveAmountXmin = proxy.toMoveAmount(tokenInfoX, amountXmin);
            uint64 moveAmountYmin = proxy.toMoveAmount(tokenInfoY, amountYmin);

            data = new bytes[](4);
            data[0] = crossVM.encodeU64(moveAmountX);
            data[1] = crossVM.encodeU64(moveAmountY);
            data[2] = crossVM.encodeU64(moveAmountXmin);
            data[3] = crossVM.encodeU64(moveAmountYmin);

            coins = new bytes[](2);
            coins[0] = tokenInfoX.moveType;
            coins[1] = tokenInfoY.moveType;
        }

        crossVM.callMove(handler, "swap", "add_liquidity", data, coins);

        protalX.withdraw(msg.sender);
        protalY.withdraw(msg.sender);
        protalLp.withdraw(msg.sender);
    }

    function bytesToAddress(
        bytes memory data
    ) private pure returns (address addr) {
        require(data.length == 20, "Invalid length in decoding address");
        assembly {
            addr := mload(add(data, 20))
        }
    }

    function handleSetLPToken(
        string memory caller,
        bytes[] memory data
    ) public returns (bytes memory) {
        require(msg.sender == address(crossVM), "Incorrect invoker");
        require(
            keccak256(bytes(caller)) ==
                keccak256(
                    bytes(
                        "0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06::swap::CallType"
                    )
                ),
            "Incorrect sender"
        );

        address lpToken = bytesToAddress(data[0]);
        address tokenX = address(proxy.sigToToken(keccak256(data[1])));
        address tokenY = address(proxy.sigToToken(keccak256(data[2])));
        _setLpToken(lpToken, tokenX, tokenY);

        return new bytes(0);
    }

    function _setLpToken(
        address lpToken,
        address tokenX,
        address tokenY
    ) internal {
        bytes32 lpSign = _lpTokenSign(tokenX, tokenY);
        require(lpTokenPool[lpSign] == address(0x0), "Duplicate register");
        lpTokenPool[lpSign] = lpToken;
        lpTokenToTokens[lpToken] = SwapPool({tokenX: tokenX, tokenY: tokenY});
    }

    function getLpToken(
        address tokenX,
        address tokenY
    ) public view returns (address) {
        bytes32 lpSign = _lpTokenSign(tokenX, tokenY);
        require(lpTokenPool[lpSign] != address(0x0), "Unknown pool");
        return lpTokenPool[lpSign];
    }

    function _lpTokenSign(
        address tokenX,
        address tokenY
    ) internal pure returns (bytes32 lpSign) {
        if (tokenX < tokenY) {
            lpSign = keccak256(abi.encodePacked(tokenX, tokenY));
        } else {
            lpSign = keccak256(abi.encodePacked(tokenY, tokenX));
        }
    }
}
