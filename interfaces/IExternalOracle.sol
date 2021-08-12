// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

interface IExternalOracle {
  /// @dev Returns the price in terms of ETH for the given token, multiplifed by 2**112.
  function getETHPx(address token) external view returns (uint);
}
