// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

interface IBetaOracle {
  /// @dev Returns the given asset price in ETH (wei), multiplied by 2**112.
  /// @param token The token to query for asset price
  function getAssetETHPrice(address token) external returns (uint);

  /// @dev Returns the given asset value in ETH (wei)
  /// @param token The token to query for asset value
  /// @param amount The amount of token to query
  function getAssetETHValue(address token, uint amount) external returns (uint);

  /// @dev Returns the conversion from amount of from` to `to`.
  /// @param from The source token to convert.
  /// @param to The destination token to convert.
  /// @param amount The amount of token for conversion.
  function convert(
    address from,
    address to,
    uint amount
  ) external returns (uint);
}
