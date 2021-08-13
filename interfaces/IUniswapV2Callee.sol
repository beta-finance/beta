// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

interface IUniswapV2Callee {
  function uniswapV2Call(
    address sender,
    uint amount0,
    uint amount1,
    bytes calldata data
  ) external;
}
