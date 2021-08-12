// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

import '../../interfaces/IExternalOracle.sol';

contract MockExternalOracle is IExternalOracle {
  mapping(address => uint) public prices;

  function getETHPx(address token) external view override returns (uint) {
    return prices[token];
  }

  function setETHPrice(address token, uint price) external returns (uint) {
    prices[token] = price;
  }
}
