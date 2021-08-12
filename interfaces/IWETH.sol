// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

interface IWETH {
  function deposit() external payable;

  function withdraw(uint wad) external;

  function approve(address guy, uint wad) external returns (bool);
}
