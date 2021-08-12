// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

interface ISwapRouter {
  struct ExactInputParams {
    bytes path;
    address recipient;
    uint deadline;
    uint amountIn;
    uint amountOutMinimum;
  }

  struct ExactOutputParams {
    bytes path;
    address recipient;
    uint deadline;
    uint amountOut;
    uint amountInMaximum;
  }

  function exactInput(ExactInputParams calldata params) external payable returns (uint amountOut);

  function exactOutput(ExactOutputParams calldata params) external payable returns (uint amountIn);

  function factory() external view returns (address);

  function refundETH() external payable;
}
