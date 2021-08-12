// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

contract MockUniswapV2Pair {
  uint112 public reserve0;
  uint112 public reserve1;
  uint32 public blockTimestampLast;
  uint public price0CumulativeLast;
  uint public price1CumulativeLast;

  function setReserves(uint112 _reserve0, uint112 _reserve1) external {
    uint32 blockTimestamp = uint32(block.timestamp);
    unchecked {
      uint32 timeElapsed = blockTimestamp - blockTimestampLast;
      if (timeElapsed > 0 && reserve0 > 0 && reserve1 > 0) {
        price0CumulativeLast += ((uint(reserve1) << 112) / uint(reserve0)) * timeElapsed;
        price1CumulativeLast += ((uint(reserve0) << 112) / uint(reserve1)) * timeElapsed;
      }
    }
    reserve0 = _reserve0;
    reserve1 = _reserve1;
    blockTimestampLast = blockTimestamp;
  }

  function getReserves()
    external
    view
    returns (
      uint112,
      uint112,
      uint32
    )
  {
    return (reserve0, reserve1, blockTimestampLast);
  }
}
