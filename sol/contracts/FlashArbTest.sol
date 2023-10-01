//SPDX-License-Identifier: Unlicense
pragma solidity ^0.8.10;
pragma abicoder v2;
// Uniswap
import "./sol_lib/uniswap/contracts/interfaces/ISwapRouter.sol";
import "./sol_lib/uniswap/contracts/interfaces/IQuoter.sol";
//import "./contracts/IQuoter.sol";
//import "./contracts/ISwapRouter.sol";

// AAVE Core
import "./sol_lib/aave/contracts/flashloan/base/FlashLoanSimpleReceiverBase.sol";
import "./sol_lib/aave/contracts/interfaces/IPoolAddressesProvider.sol";
//import {FlashLoanSimpleReceiverBase} from "@aave/core-v3/contracts/flashloan/base/FlashLoanSimpleReceiverBase.sol";
//import {IPoolAddressesProvider} from "@aave/core-v3/contracts/interfaces/IPoolAddressesProvider.sol";
//import "./sol_lib/aave/contracts/dependencies/openzeppelin/contracts/IERC20.sol";
//import "./sol_lib/aave/contracts/dependencies/openzeppelin/contracts/Ownable.sol";
//import "./contracts/Ownable.sol"
//import "./contracts/Owner.sol";

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

interface IWETH is IERC20 {
    function deposit() external payable;
    function withdraw(uint amount) external;
}


//contract FlashArb is FlashLoanSimpleReceiverBase, Ownable {
contract FlashArbTest is FlashLoanSimpleReceiverBase {

    address payable owner;
    address poolAddressProvider = 0xC911B590248d127aD18546B186cC6B324e99F02c;
    //address poolAddressProvider = 0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb; //ARBBITRUM_MAINNET
    constructor(address _addressProvider) FlashLoanSimpleReceiverBase(IPoolAddressesProvider(_addressProvider)) {
        owner = payable(msg.sender);
    }

    // Uniswap
    address public constant uniswapRouterAddress = 0xE592427A0AEce92De3Edee1F18E0157C05861564;
    address public constant uinswapQuoterAddress = 0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6;
    ISwapRouter public constant uniswapRouter = ISwapRouter(uniswapRouterAddress);
    IQuoter public constant uniswapQuoter = IQuoter(uinswapQuoterAddress);

    // SushiSwap
    address public constant sushiSwapRouterAddress = 0x8A21F6768C1f8075791D08546Dadf6daA0bE820c;
    address public constant sushiSwapQuoterAddress = 0x0524E833cCD057e4d7A296e3aaAb9f7675964Ce1;
    ISwapRouter public constant sushiSwapRouter = ISwapRouter(sushiSwapRouterAddress);
    IQuoter public constant sushiSwapQuoter = IQuoter(sushiSwapQuoterAddress);

    /*
    bytes public swap1_param;
    bytes public swap2_param;
    bytes public swap3_param;
    bytes public encoded_swaps_param;
    */


    // AAVE
    address public flashLoanInitiator;

    uint256 public resultAmountOut;
    bool public arbitrage;

    enum Dex {
        UNI, // 0
        SUSHI // 1
    }

    struct ArbitrageParams {
        address tokenIn; // token0
        address tokenOut; // token1
        uint24 fee; // swap#_pool_fee
        uint256 amountOut; // swap#_amount_out
        uint256 amountInMaximum; // amoun_in or swap#_amount_out
        uint160 sqrtPriceLimitX96; // swap#_sqrt_price_x96
        uint8 dex; // swap#_dex --> enum Dex
    }
    //mapping (bytes => Arbitrage) public arbitrageOpportunities;

    event Arbitrage(bytes path, uint256 amountIn, bool isArbitrage);
    event Swap(bytes path, uint256 amountIn, uint256 amountOut);
    event Quote(bytes swap, uint256 amountIn, uint256 amountOut);

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

        //initFlashLoanMultiHopSwap(asset, params, amount);
        crossDexTriArbitrageSwaps(params);
        uint256 amountOwed = amount + premium;
        IERC20(asset).approve(address(POOL), amountOwed);

        return true;
    }
    function testCrossDexTriArbSwaps(
        bytes calldata swap1,
        bytes calldata swap2,
        bytes calldata swap3
    ) public returns (bool) {
        bool success;

        bytes memory params = abi.encode(
            swap1,
            swap2,
            swap3
        );
        /*
        swap1_param = swap1;
        swap2_param = swap2;
        swap3_param = swap3;
        encoded_swaps_param = params;
        */
        success = crossDexTriArbitrageSwaps(params);

        return success;
    }

    function crossDexTriArbitrageSwaps(bytes memory params) internal returns(bool){
        bytes memory swap1;
        bytes memory swap2;
        bytes memory swap3;
        bool swap1_result = false;
        bool swap2_result = false;
        bool swap3_result = false;

        (swap1, swap2, swap3) = abi.decode(params, (bytes, bytes, bytes));
        //swap1_param = swap1;
        //swap2_param = swap2;
        //swap3_param = swap3;


        //swap1_result = exactOutputDexSwap(swap1);
        //swap2_result = exactOutputDexSwap(swap2);

        swap1_result = exactInputDexSwap(swap1);
        swap2_result = exactInputDexSwap(swap2);
        swap3_result = exactInputDexSwap(swap3);

        return true;
    }

    ISwapRouter.ExactOutputSingleParams  public routerParamsExactOutput;
    string public dexName;
    function exactOutputDexSwap (bytes memory swap) internal returns(bool) {

        address tokenIn;
        address tokenOut;
        uint24 fee;
        uint256 amountOut;
        uint256 amountInMaximum;
        uint160 sqrtPriceLimitX96;
        uint8 dex;
        uint256 amountIn;


        ISwapRouter.ExactOutputSingleParams memory params;

        (
            tokenIn,
            tokenOut,
            fee,
            amountOut,
            amountInMaximum,
            sqrtPriceLimitX96,
            dex
        ) = abi.decode(swap, (address, address, uint24, uint256, uint256, uint160, uint8));

        params = ISwapRouter.ExactOutputSingleParams ({
            tokenIn: tokenIn,
            tokenOut: tokenOut,
            fee: fee,
            recipient: address(this),
            deadline: block.timestamp,
            amountOut: amountOut,
            amountInMaximum: amountInMaximum,
            sqrtPriceLimitX96: sqrtPriceLimitX96
        });

        routerParamsExactOutput = params;

        if (dex == 0) {
            // Approve uniswap router for tokenIn
            dexName = "UNI";
            IERC20(tokenIn).approve(uniswapRouterAddress, amountInMaximum);
            amountIn = uniswapRouter.exactOutputSingle(params);
            emit Swap(swap, amountIn, amountOut);
        }
        else if (dex == 1) {
            // Approve sushiswap router for tokenIn
            dexName = "SUSHI";
            /*
            IERC20(tokenIn).approve(sushiSwapRouterAddress, amountInMaximum);
            amountIn = sushiSwapRouter.exactOutputSingle(params);
            emit Swap(swap, amountIn, amountOut);
            */
        }
        else {
            return false;
        }

        return true;
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
        uint256 amountOutCatch;

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

        if (dex == 0) {
            // Approve uniswap router for tokenIn
            dexName = "UNI";
            IERC20(tokenIn).approve(uniswapRouterAddress, amountIn);
            try uniswapRouter.exactInputSingle(params) returns(uint256 amountOut){
                emit Swap(swap, amountIn, amountOut);
            } catch {
                params.amountIn = IERC20(tokenIn).balanceOf(address(this));
                amountOutCatch = uniswapRouter.exactInputSingle(params);
                emit Swap(swap, amountIn, amountOutCatch);
            }
        }
        else if (dex == 1) {
            // Approve sushiswap router for tokenIn
            dexName = "SUSHI";
            IERC20(tokenIn).approve(sushiSwapRouterAddress, amountIn);
            try sushiSwapRouter.exactInputSingle(params) returns(uint256 amountOut){
                emit Swap(swap, amountIn, amountOut);
            } catch {
                params.amountIn = IERC20(tokenIn).balanceOf(address(this));
                amountOutCatch = sushiSwapRouter.exactInputSingle(params);
                emit Swap(swap, amountIn, amountOutCatch);
            }
        }
        else {
            return false;
        }

        return true;
    }
    /*
        address token1,
        address token2,
        uint24 feeTier1,
        uint24 feeTier2,
        uint24 feeTier3,
    */
    function flashLoanArbitrage(
        address token0,
        address token1,
        address token2,
        uint24 feeTier1,
        uint24 feeTier2,
        uint24 feeTier3,
        uint256 amountIn
    ) public {
        bytes memory params = abi.encodePacked(
            token0,
            feeTier1,
            token1,
            feeTier2,
            token2,
            feeTier3,
            token0
        );
        uint16 referralCode = 0;

        POOL.flashLoanSimple(
            address(this),
            token0,
            amountIn,
            params,
            referralCode
        );
    }

    function flashLoanTriArbitrageCrossDex(
        address token0,
        uint256 loanAmount,
        bytes calldata swap1,
        bytes calldata swap2,
        bytes calldata swap3
    ) external {

        bytes memory params = abi.encode(
            swap1,
            swap2,
            swap3
        );


        uint16 referralCode = 0;
        POOL.flashLoanSimple(
            address(this),
            token0,
            loanAmount,
            params,
            referralCode
        );
    }

    // Check for arbitrage between dexes or tri opportunity on single dex


    function checkSingleDexArbitrage (
        address token0,
        address token1,
        address token2,
        uint24 feeTier1,
        uint24 feeTier2,
        uint24 feeTier3,
        uint256 amountIn
    ) external {
        bytes memory path;
        //bool arb;

        path = abi.encodePacked(
            token0,
            feeTier1,
            token1,
            feeTier2,
            token2,
            feeTier3,
            token0
        );

        // Check for arb on single dex
        arbitrage = checkSingleDexTriArb(path, amountIn);

    }

    function checkSingleDexTriArb (
        bytes memory path,
        uint256 amountIn
    ) internal returns(bool){
        bool arb;
        //bytes uniqueId;
        uint256 amountOut;

        // Check uniswap Quoter for arb
        amountOut = uniswapQuoter.quoteExactInput(
            path,
            amountIn
        );

        if(resultAmountOut > amountIn) {
            arb = true;
        }
        else {
            arb = false;
        }
        emit Arbitrage(path, amountIn, arb);
        return arb;
    }

    function multiHopSwap(
        address token0,
        bytes memory path,
        uint256 amountIn
    ) internal returns (uint256) {
        uint256 swapOut;
        ISwapRouter.ExactInputParams memory params;

        // Need to approve token first via wallet
        IERC20(token0).transferFrom(msg.sender, address(this), amountIn);
        IERC20(token0).approve(uniswapRouterAddress, amountIn);

        params = ISwapRouter.ExactInputParams({
            path: path,
            recipient: msg.sender,
            deadline: block.timestamp + 300,
            amountIn: amountIn,
            amountOutMinimum: 0
        });

        swapOut = uniswapRouter.exactInput(params);
        return swapOut;
    }

    function flashLoanMultiHopSwap(
        address token0,
        bytes memory path,
        uint256 amountIn
    ) internal returns (uint256) {
        uint256 amountOut;
        ISwapRouter.ExactInputParams memory params;

        IERC20(token0).approve(uniswapRouterAddress, amountIn);

        params = ISwapRouter.ExactInputParams({
            path: path,
            recipient: address(this),
            deadline: block.timestamp + 300,
            amountIn: amountIn,
            amountOutMinimum: 0
        });

        amountOut = uniswapRouter.exactInput(params);
        emit Swap(path, amountIn, amountOut);

        return amountOut;
    }

    function initFlashLoanMultiHopSwap(
        address token0,
        bytes memory path,
        uint256 amountIn
    ) internal {
        resultAmountOut = flashLoanMultiHopSwap(token0, path, amountIn);
    }

    function initMultiHopSwap(
        address token0,
        address token1,
        address token2,
        uint24 poolFee1,
        uint24 poolFee2,
        uint24 poolFee3,
        uint256 amountIn
    ) external {
        bytes memory path;

        path = abi.encodePacked(
            token0,
            poolFee1,
            token1,
            poolFee2,
            token2,
            poolFee3,
            token0
        );

        resultAmountOut = multiHopSwap(token0, path, amountIn);
    }

    /*
        @param swap --> abi.encoded value that contains the params for the quoter (tokenIn, tokenOut, fee, amountIn, amountOutMinimum,
        sqrtPriceLimitX96)
        @param dex: Integer value to determine which uniswapv3 quoter to use (currently on uniswap and sushiswap only)
        Description: Function to statically call uniswapv3 quoter to estimate swaps. Using the function as a view will prevent
        gas charge
    */
    function uniswapV3ExactInputSingleQuote(bytes calldata swap) public returns(uint256 amountOut) {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
        uint8 dex;
        uint256 quoteAmountOut;

        (
            tokenIn,
            tokenOut,
            fee,
            amountIn,
            amountOutMinimum,
            sqrtPriceLimitX96,
            dex
        ) = abi.decode(swap, (address, address, uint24, uint256, uint256, uint160, uint8));

        if (dex == 0) {
            quoteAmountOut = uniswapQuoter.quoteExactInputSingle(
                tokenIn,
                tokenOut,
                fee,
                amountIn,
                sqrtPriceLimitX96
            );
        } else if (dex == 1) {
            quoteAmountOut = sushiSwapQuoter.quoteExactInputSingle(
                tokenIn,
                tokenOut,
                fee,
                amountIn,
                sqrtPriceLimitX96
            );
        }

        emit Quote(swap, amountIn, quoteAmountOut);

        return amountOut;
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

    function tokenApprove(address spender, address token, uint256 amount) external {
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