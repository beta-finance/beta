// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

import '../BetaBank.sol';

contract MockIsPermittedCallerTester {
  BetaBank public immutable betaBank;

  constructor(BetaBank _betaBank) {
    betaBank = _betaBank;
  }

  function checkIsPermittedCaller(address _owner, address _sender) external returns (bool) {
    return betaBank.isPermittedCaller(_owner, _sender);
  }
}
