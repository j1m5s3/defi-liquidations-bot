//SPDX-License-Identifier: Unlicense
pragma solidity ^0.8.10;
pragma abicoder v2;

// Custom implementations
//import "./sol_lib/UniswapOperations.sol";
// Uniswap
import "./sol_lib/uniswap/contracts/interfaces/ISwapRouter.sol";
import "./sol_lib/uniswap/contracts/interfaces/IQuoter.sol";
import "./sol_lib/uniswap/contracts/libraries/SqrtPriceMath.sol";

// AAVE Core
import "./sol_lib/aave/contracts/flashloan/base/FlashLoanSimpleReceiverBase.sol";
import "./sol_lib/aave/contracts/interfaces/IPoolAddressesProvider.sol";
import "./sol_lib/aave/contracts/interfaces/IPool.sol";

// ERC20 token interface
//import "./sol_lib/aave/contracts/dependencies/openzeppelin/contracts/IERC20.sol";
interface IERC20 {
	function totalSupply() external view returns (uint);
	function balanceOf(address account) external view returns (uint);
	function transfer(address recipient, uint amount) external returns (bool);
	function allowance(address owner, address spender) external view returns (uint);
	function approve(address spender, uint amount) external returns (bool);
	function transferFrom(address sender, address recipient, uint amount) external returns (bool);
	event Transfer(address indexed from, address indexed to, uint value);
	event Approval(address indexed owner, address indexed spender, uint value);
}

contract FlashArb is FlashLoanSimpleReceiverBase {

    //UniswapOperations uniswapOperations = new UniswapOperations();

    address payable owner;
    constructor(address _addressProvider) FlashLoanSimpleReceiverBase(IPoolAddressesProvider(_addressProvider)) {
        owner = payable(msg.sender);
    }

    // AAVE_ARBITRUM
    address public flashLoanInitiator;
    address public AAVE_POOL_CONTRACT_ADDRESS_ARBITRUM = 0x794a61358D6845594F94dc1DB02A252b5b4814aD;
    address public RADIANT_POOL_CONTRACT_ADDRESS_ARBITRUM = 0xF4B1486DD74D07706052A33d31d7c0AAFD0659E1;
    IPool public constant aavePool = IPool(AAVE_POOL_CONTRACT_ADDRESS_ARBITRUM);
    IPool public constant radiantPool = IPool(RADIANT_POOL_CONTRACT_ADDRESS_ARBITRUM);

    // Uniswap Arbitrum
    address public constant UNISWAP_ROUTER_ADDRESS = 0xE592427A0AEce92De3Edee1F18E0157C05861564;
    address public constant UNISWAP_QUOTER_ADDRESS = 0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6;
    ISwapRouter public constant uniswapRouter = ISwapRouter(UNISWAP_ROUTER_ADDRESS);
    IQuoter public constant uniswapQuoter = IQuoter(UNISWAP_QUOTER_ADDRESS);

    event Arbitrage(bytes path, uint256 amountIn, bool isArbitrage);
    event Swap(bytes path, uint256 amountIn, uint256 amountOut);
    event Quote(bytes swap, uint256 amountIn, uint256 amountOut);
    event FlashLoanResult(uint256 loanAmount, uint256 balancePaid, uint256 newTokenBalance);
    event TxnReverted(bytes swap, uint256 amountIn, uint8 dexId);

    // Function to receive Ether. msg.data must be empty
    receive() external payable {}

    // Fallback function is called when msg.data is not empty
    fallback() external payable {}

    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        flashLoanInitiator = initiator;

        require(IERC20(asset).balanceOf(address(this)) >= amount, "RECEIVED_LOANED_AMOUNT_INSUFFICIENT");
        liquidatePosition(params);

        uint256 amountOwed = amount + premium;
        require(IERC20(asset).balanceOf(address(this)) >= amountOwed, "NOT_ENOUGH_FUNDS_TO_PAY_BACK_LOAN");

        IERC20(asset).approve(address(POOL), amountOwed);

        uint256 tokenBalance = IERC20(asset).balanceOf(address(this)) - amountOwed;

        emit FlashLoanResult(amount, amountOwed, tokenBalance);

        return true;
    }

    function flashLoanLiquidate(
        address token0,
        uint256 loanAmount,
        bytes calldata liquidateParams
    ) external onlyOwner {

        uint16 referralCode = 0;
        POOL.flashLoanSimple(
            address(this),
            token0,
            loanAmount,
            params,
            referralCode
        );
    }

    function liquidatePosition(bytes calldata liquidateParams) external onlyOwner {
        address collateralAsset;
        address debtAsset;
        address user;
        uint256 debtToCover;
        bool receiveAToken;
        strimg memory protocol;

        (
            collateralAsset,
            debtAsset,
            user,
            debtToCover,
            receiveAToken
        ) = abi.decode(liquidateParams, (address, address, address, uint256, bool));


        if (protocol == "AAVE_ARBITRUM") {
            IERC20(debtAsset).approve(address(AAVE_POOL_CONTRACT_ADDRESS_ARBITRUM), debtToCover);

            aavePool.liquidationCall(
                collateralAsset,
                debtAsset,
                user,
                debtToCover,
                receiveAToken
            );

        } else if (protocol == "RADIANT_ARBITRUM") {
            IERC20(debtAsset).approve(RADIANT_POOL_CONTRACT_ADDRESS_ARBITRUM, debtToCover);

            radiantPool.liquidationCall(
                collateralAsset,
                debtAsset,
                user,
                debtToCover,
                receiveAToken
            );

            IERC20(collateralAsset).approve(RADIANT_POOL_CONTRACT_ADDRESS_ARBITRUM, IERC20(collateralAsset).balanceOf(address(this)));


        } else {
            revert("INVALID_PROTOCOL");
        }


    }

    ISwapRouter.ExactInputSingleParams public routerParamsExactInput;
    function exactInputDexSwap (bytes memory swap) internal returns(bool) {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
        uint8 dex;

        ISwapRouter.ExactInputSingleParams memory params;

        (
            tokenIn,
            tokenOut,
            fee,
            amountIn,
            amountOutMinimum,
            sqrtPriceLimitX96,
            dex
        ) = abi.decode(swap, (address, address, uint24, uint256, uint256, uint160, uint8));

        require(IERC20(tokenIn).balanceOf(address(this)) >= amountIn, "TOKEN_IN_BALANCE_INSUFFICIENT");

        params = ISwapRouter.ExactInputSingleParams ({
            tokenIn: tokenIn,
            tokenOut: tokenOut,
            fee: fee,
            recipient: address(this),
            deadline: block.timestamp,
            amountIn: amountIn,
            amountOutMinimum: amountOutMinimum,
            sqrtPriceLimitX96: sqrtPriceLimitX96
        });
        routerParamsExactInput = params;

        if (dex == 1) {
            // Approve uniswap router for tokenIn
            IERC20(tokenIn).approve(uniswapRouterAddress, amountIn + 1);

            uint256 amountOut = uniswapRouter.exactInputSingle(params);
            require(amountOut >= amountOutMinimum, "AMOUNT_OUT_MINIMUM_NOT_MET");

            emit Swap(swap, amountIn, amountOut);
            /*
            try uniswapRouter.exactInputSingle(params) returns(uint256 amountOut){
                emit Swap(swap, amountIn, amountOut);
            } catch {
                emit TxnReverted(swap, amountIn, dex);
				return false;
            }
            */
        }
        else if (dex == 2) {
			// Approve sushiswap router for tokenIn
            IERC20(tokenIn).approve(sushiSwapRouterAddress, amountIn + 1);

            uint256 amountOut = sushiSwapRouter.exactInputSingle(params);
            require(amountOut >= amountOutMinimum, "AMOUNT_OUT_MINIMUM_NOT_MET");

            emit Swap(swap, amountIn, amountOut);
            /*
            try sushiSwapRouter.exactInputSingle(params) returns(uint256 amountOut){
                emit Swap(swap, amountIn, amountOut);
            } catch {
                emit TxnReverted(swap, amountIn, dex);
				return false;
            }
            */
        }
        else {
            return false;
        }

        return true;
    }


    //function getArbitrageOpportunity (int index)
    function getTokenBalance(address token, address holder) public view returns(uint256) {
        uint256 balance = IERC20(token).balanceOf(holder);
        return balance;
    }

    function getETHBalance() public view returns(uint256) {
        uint256 balance = msg.sender.balance;
        return balance;
    }

    function checkTokenApprovalAllowance(address token) public view returns (uint256) {
        uint256 allowance = IERC20(token).allowance(msg.sender, address(this));
        return allowance;
    }

    function checkContractTokenApprovalAllowance(address token, address approvedAddress) public view returns(uint256) {
        uint256 allowance = IERC20(token).allowance(address(this), approvedAddress);
        return allowance;
    }

    function transferTokensFrom(address token, uint256 amount) external {
        IERC20(token).transferFrom(msg.sender, address(this), amount);
    }

    function transferTokensTo(address token, address to, uint256 amount) external onlyOwner{
        IERC20(token).transfer(to, amount);
    }

    function tokenApprove(address spender, address token, uint256 amount) external onlyOwner {
        IERC20(token).approve(spender, amount);
    }

    function getCurrentBlockTime() public view returns(uint256) {
        return block.timestamp;
    }

    modifier onlyOwner() {
        require(
            msg.sender == owner,
            "Only the contract owner can call this function"
        );
        _;
    }

}