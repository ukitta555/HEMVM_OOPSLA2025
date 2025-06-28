// SPDX-License-Identifier: MIT
pragma solidity ^0.8.6;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "./cross_space/coin/CrossVmProxyCompound.sol";


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


interface CEth {
    function mint() external payable;

    function borrow(uint256) external returns (uint256);

    function repayBorrow() external payable;

    function borrowBalanceCurrent(address) external returns (uint256);
}


interface Comptroller {
    function markets(address) external returns (bool, uint256);

    function enterMarkets(address[] calldata)
        external
        returns (uint256[] memory);

    function getAccountLiquidity(address)
        external
        view
        returns (uint256, uint256, uint256);
}


interface PriceFeed {
    function getUnderlyingPrice(address cToken) external view returns (uint);
}


contract MyContract {
    event MyLog(string, uint256);
    CrossVmProxyCompound crossVmProxy =
       CrossVmProxyCompound(0xcC166f312524Cc88E2c16c3bdd5735a23376B1fb);

    function borrowEthExample(
        address _cTokenToBorrow,
        address _cTokenAddress,
        address _underlyingAddress,
        uint256 _underlyingToSupplyAsCollateral
    ) public returns (uint) {
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

        uint256 borrows = cTokenToBorrow.borrowBalanceCurrent(address(this));
        emit MyLog("Current ETH borrow amount", borrows);


        return borrows;
    }


    function myEthRepayBorrow(address _cTokenToRepay, address _cTokenAddress, address underlying, uint256 amount)
        public
        returns (bool)
    {
        CErc20 cTokenToRepay = CErc20(_cTokenToRepay);
        CErc20 cToken = CErc20(_cTokenAddress);
        Erc20 tokenToRepay = Erc20(underlying);
        tokenToRepay.approve(_cTokenToRepay, 1000 ether);
        cTokenToRepay.repayBorrow(amount);
        cToken.redeem(cToken.balanceOf(address(this)));
        return true;
    }

    // Need this to receive ETH when `borrowEthExample` executes
    receive() external payable {}
}
