// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

interface IPancakeCallee {
  function pancakeCall(
    address sender,
    uint amount0,
    uint amount1,
    bytes calldata data
  ) external;
}
