//SPDX-License-Identifier: Unlicense
pragma solidity ^0.8.10;
pragma abicoder v2;
// Uniswap
import "./uniswap/contracts/interfaces/ISwapRouter.sol";
import "./uniswap/contracts/interfaces/IQuoter.sol";

// ERC20 token interface
import "./aave/contracts/dependencies/openzeppelin/contracts/IERC20.sol";

contract UniswapOperations {
	// Uniswap Arbitrum
    address public constant uniswapRouterAddress = 0xE592427A0AEce92De3Edee1F18E0157C05861564;
    address public constant uinswapQuoterAddress = 0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6;
    ISwapRouter public constant uniswapRouter = ISwapRouter(uniswapRouterAddress);
    IQuoter public constant uniswapQuoter = IQuoter(uinswapQuoterAddress);

    // SushiSwap Arbitrum
    address public constant sushiSwapRouterAddress = 0x8A21F6768C1f8075791D08546Dadf6daA0bE820c;
    address public constant sushiSwapQuoterAddress = 0x0524E833cCD057e4d7A296e3aaAb9f7675964Ce1;
    ISwapRouter public constant sushiSwapRouter = ISwapRouter(sushiSwapRouterAddress);
    IQuoter public constant sushiSwapQuoter = IQuoter(sushiSwapQuoterAddress);

	event Swap(bytes path, uint256 amountIn, uint256 amountOut);
    event Quote(bytes swap, uint256 amountIn, uint256 amountOut);
	event TxnReverted(bytes swap, uint256 amountIn, uint8 dexId);

	ISwapRouter.ExactInputSingleParams public routerParamsExactInput;
    function exactInputDexSwap (bytes memory swap) external returns(bool) {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
        uint8 dex;
        uint256 amountOut;

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

        if (dex == 1) {
            // Approve uniswap router for tokenIn
            IERC20(tokenIn).approve(uniswapRouterAddress, amountIn);
			amountOut = uniswapRouter.exactInputSingle(params);
			emit Swap(swap, amountIn, amountOut);
            try uniswapRouter.exactInputSingle(params) returns(uint256 amountOut){
                emit Swap(swap, amountIn, amountOut);
            } catch {
                emit TxnReverted(swap, amountIn, dex);
				return false;
            }
        }
        else if (dex == 2) {
			// Approve sushiswap router for tokenIn
            IERC20(tokenIn).approve(sushiSwapRouterAddress, amountIn);
            try sushiSwapRouter.exactInputSingle(params) returns(uint256 amountOut){
                emit Swap(swap, amountIn, amountOut);
            } catch {
                emit TxnReverted(swap, amountIn, dex);
				return false;
            }
        }
        else {
            return false;
        }

        return true;
    }

	ISwapRouter.ExactOutputSingleParams  public routerParamsExactOutput;
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

        if (dex == 1) {
            // Approve uniswap router for tokenIn
            IERC20(tokenIn).approve(uniswapRouterAddress, amountInMaximum);
            amountIn = uniswapRouter.exactOutputSingle(params);
            emit Swap(swap, amountIn, amountOut);
        }
        else if (dex == 2) {
            // Approve sushiswap router for tokenIn
            IERC20(tokenIn).approve(sushiSwapRouterAddress, amountInMaximum);
            amountIn = sushiSwapRouter.exactOutputSingle(params);
            emit Swap(swap, amountIn, amountOut);
        }
        else {
            return false;
        }

        return true;
    }

	/*
        @param swap --> abi.encoded value that contains the params for the quoter (tokenIn, tokenOut, fee, amountIn, amountOutMinimum,
        sqrtPriceLimitX96)
        @param dex: Integer value to determine which uniswapv3 quoter to use (currently on uniswap and sushiswap only)
        Description: Function to statically call uniswapv3 quoter to estimate swaps. Using the function as a view will prevent
        gas charge
    */
	function uniswapV3ExactInputSingleQuote(bytes calldata swap) external {
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
    }



	function multiHopSwap(
        address token0,
        bytes memory path,
        uint256 amountIn
    ) external returns (uint256) {
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

}
