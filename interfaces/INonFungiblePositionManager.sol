// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

interface INonFungiblePositionManager {
  struct MintParams {
    address token0;
    address token1;
    uint24 fee;
    int24 tickLower;
    int24 tickUpper;
    uint amount0Desired;
    uint amount1Desired;
    uint amount0Min;
    uint amount1Min;
    address recipient;
    uint deadline;
  }

  function mint(MintParams calldata params)
    external
    payable
    returns (
      uint tokenId,
      uint128 liquidity,
      uint amount0,
      uint amount1
    );
}
