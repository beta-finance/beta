// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

contract BetaRunnerWithCallback {
  address private constant NO_CALLER = address(42); // nonzero so we don't repeatedly clear storage
  address private caller = NO_CALLER;

  modifier withCallback() {
    require(caller == NO_CALLER);
    caller = msg.sender;
    _;
    caller = NO_CALLER;
  }

  modifier isCallback() {
    require(caller == tx.origin);
    _;
  }
}
