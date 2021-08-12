// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

import '../../interfaces/IUniswapV2Factory.sol';

contract MockUniswapV2Factory is IUniswapV2Factory {
  mapping(address => mapping(address => address)) public pairs;

  function createPair(address tokenA, address tokenB) external override returns (address pair) {
    // NOT IMPLEMENTED
    revert();
  }

  function setPair(
    address tokenA,
    address tokenB,
    address pair
  ) external {
    pairs[tokenA][tokenB] = pair;
    pairs[tokenB][tokenA] = pair;
  }

  function getPair(address tokenA, address tokenB) external view override returns (address) {
    address pair = pairs[tokenA][tokenB];
    require(pair != address(0), 'getPair/no-pair');
    return pair;
  }
}
