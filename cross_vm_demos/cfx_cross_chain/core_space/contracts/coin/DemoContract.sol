import "./VaultErc20.sol";
import "../interfaces/ICrossVmErc20.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract DemoContract {

    function demoDeposit20Withdraw10(
        address vaultAddress,
        bytes20 eSpaceProxyAddress,
        bytes20 someOtherAddress,
        address myAddress,
        address tokenAddress
    ) external {
        IERC20(tokenAddress).approve(vaultAddress, type(uint256).max);
        IERC20(tokenAddress).transferFrom(msg.sender, address(this), 20 * (10 ** 18));
        ICrossVmErc20(vaultAddress).deposit(eSpaceProxyAddress, 10 ether); // ether == 10 ** 18 multiplier
        ICrossVmErc20(vaultAddress).deposit(someOtherAddress, 10 ether); // ether == 10 ** 18 multiplier
        // withdraws only 10 tokens that were deposited to proxy
        // in case we wanted to withdraw all 20, someOtherAddress would have to return them to proxy after performing the required operation
        ICrossVmErc20(vaultAddress).withdraw(myAddress);
    }
}