// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;
import "../coin/CrossVmProxyCompound.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";

interface Erc20 {
    function approve(address, uint256) external returns (bool);

    function transfer(address, uint256) external returns (bool);
}


interface CErc20 {
    function mint(uint256) external returns (uint256);

    function borrow(uint256) external returns (uint256);

    function borrowRatePerBlock() external view returns (uint256);

    function borrowBalanceCurrent(address) external returns (uint256);

    function repayBorrow(uint256) external returns (uint256);

    function redeem(uint256) external returns (uint256);

    function balanceOf(address) external view returns (uint256);
}


contract CrossCompoundWrapper {
    ICrossVM constant crossVM =
        ICrossVM(0x0888000000000000000000000000000000000006);
    CrossVmProxyCompound crossVmProxy =
       CrossVmProxyCompound(0xcC166f312524Cc88E2c16c3bdd5735a23376B1fb);

    // should be fetched from comptroller.getAllMarkets()
    // but this is a simplified Compound demo w/o comptroller so we define it here
    address public c_BorrowCoin = address(0x14529A6C979B2563207e260A6138F4026B19eE0d);
    address public c_CollateralCoin = address(0x866A4a061De0f196205dfF79B3c47700b570f617);

    bytes32 constant handler =
        0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06;

    modifier builtinCallerGuard(string memory caller) {
        require(msg.sender == address(crossVM), "Incorrect invoker");
        require(keccak256(bytes(caller)) == keccak256(bytes("0x5f61e930582ca112420399eaac4d224aba550789bd31dbe3d8835abac4267b06::cross_vm_coin_compound::CallType")), "Incorrect sender");
        _;
    }

    function handleSupplyCollateral(string memory caller, bytes[] memory data) builtinCallerGuard(caller) public returns (bytes memory) {
        bytes memory rawCoinTypeCollateral = data[0];

        IERC20Metadata collateralToken = crossVmProxy.sigToToken(keccak256(rawCoinTypeCollateral));
        crossVM.log(abi.encodePacked(address(collateralToken)));

        TokenInfo memory collateralTokenInfo = crossVmProxy.getTokenInfo(address(crossVmProxy.tokenToPortal(address(collateralToken))));

        bytes memory rawCoinTypeBorrow = data[1];

        IERC20Metadata borrowToken = crossVmProxy.sigToToken(keccak256(rawCoinTypeBorrow));
        crossVM.log(abi.encodePacked(address(borrowToken)));

        TokenInfo memory borrowTokenInfo = crossVmProxy.getTokenInfo(address(crossVmProxy.tokenToPortal(address(borrowToken))));

        uint256 amountToSupply = toEvmAmount(collateralTokenInfo, crossVM.decodeU64(data[2]));

        borrowEthExample(
            c_BorrowCoin,
            c_CollateralCoin,
            address(collateralTokenInfo.token),
            amountToSupply,
            borrowTokenInfo.token
        );

        return new bytes(0);
    }

    function handleRepayDebt(
        string memory caller,
        bytes[] memory data
    ) builtinCallerGuard(caller) public returns (bytes memory) {
        bytes memory rawCoinTypeCollateral = data[0];

        IERC20Metadata collateralToken = crossVmProxy.sigToToken(keccak256(rawCoinTypeCollateral));
        crossVM.log(abi.encodePacked(address(collateralToken)));

        TokenInfo memory collateralTokenInfo = crossVmProxy.getTokenInfo(address(crossVmProxy.tokenToPortal(address(collateralToken))));

        bytes memory rawCoinTypeBorrow = data[1];

        IERC20Metadata tokenBorrow = crossVmProxy.sigToToken(keccak256(rawCoinTypeBorrow));
        crossVM.log(abi.encodePacked(address(tokenBorrow)));

        TokenInfo memory tokenBorrowInfo = crossVmProxy.getTokenInfo(address(crossVmProxy.tokenToPortal(address(tokenBorrow))));

        uint256 amountToRepay = toEvmAmount(tokenBorrowInfo, crossVM.decodeU64(data[2]));

        // address _cTokenToRepay, address _cTokenAddress, address underlying, uint256 amount
        myEthRepayBorrow(
            c_BorrowCoin,
            c_CollateralCoin,
            address(tokenBorrowInfo.token),
            amountToRepay,
            collateralTokenInfo.token
        );

        return new bytes(0);
    }


    function borrowEthExample(
        address _cTokenToBorrow,
        address _cTokenAddress,
        address _underlyingAddress,
        uint256 _underlyingToSupplyAsCollateral,
        IERC20 borrowCoin
    ) public {
        CErc20 cTokenToBorrow = CErc20(_cTokenToBorrow);
        CErc20 cToken = CErc20(_cTokenAddress);
        Erc20 underlying = Erc20(_underlyingAddress);

        // Approve transfer of underlying
        underlying.approve(_cTokenAddress, _underlyingToSupplyAsCollateral);

        // Supply underlying as collateral, get cToken in return
        uint256 error = cToken.mint(_underlyingToSupplyAsCollateral);
        require(error == 0, "CErc20.mint Error");

        // Borrow a fixed amount of ETH below our maximum borrow amount
        uint256 numWeiToBorrow = 2000000000000000; // 0.002 ETH

        // Borrow, then check the underlying balance for this contract's address
        cTokenToBorrow.borrow(numWeiToBorrow);
        borrowCoin.transfer(address(crossVmProxy), numWeiToBorrow);
    }

    function myEthRepayBorrow(
        address _cTokenToRepay,
        address _cTokenAddress,
        address underlying,
        uint256 amount,
        IERC20 collateralToken
    ) public
    {
        CErc20 cTokenToRepay = CErc20(_cTokenToRepay);
        CErc20 cToken = CErc20(_cTokenAddress);
        Erc20 tokenToRepay = Erc20(underlying);
        tokenToRepay.approve(_cTokenToRepay, amount);
        cTokenToRepay.repayBorrow(amount);
        cToken.redeem(cToken.balanceOf(address(this)));
        collateralToken.transfer(address(crossVmProxy), collateralToken.balanceOf(address(this)));
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
