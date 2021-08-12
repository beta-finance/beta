// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

import '../BetaBank.sol';

contract MockAllowActionForTester {
  BetaBank public immutable betaBank;

  constructor(BetaBank _betaBank) {
    betaBank = _betaBank;
  }

  function checkAllowActionFor(address _owner, address _sender) external returns (bool) {
    return betaBank.allowActionFor(_owner, _sender);
  }
}
