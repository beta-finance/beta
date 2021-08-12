// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

interface IUniswapV3Pool {
  function mint(
    address recipient,
    int24 tickLower,
    int24 tickUpper,
    uint128 amount,
    bytes calldata data
  ) external returns (uint amount0, uint amount1);

  function swap(
    address recipient,
    bool zeroForOne,
    int amountSpecified,
    uint160 sqrtPriceLimitX96,
    bytes calldata data
  ) external returns (int amount0, int amount1);

  function initialize(uint160 sqrtPriceX96) external;
}
