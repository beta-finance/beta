// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

import './BetaRunnerBase.sol';

contract BetaRunnerLending is BetaRunnerBase {
  constructor(address _betaBank, address _weth) BetaRunnerBase(_betaBank, _weth) {}

  /// @dev Borrows the asset using the given collateral.
  function borrow(
    uint _pid,
    address _underlying,
    address _collateral,
    uint _amountBorrow,
    uint _amountPut
  ) external payable onlyEOA {
    _transferIn(_collateral, msg.sender, _amountPut);
    _borrow(msg.sender, _pid, _underlying, _collateral, _amountBorrow, _amountPut);
    _transferOut(_underlying, msg.sender, _amountBorrow);
  }

  /// @dev Repays the debt and takes collateral for owner.
  function repay(
    uint _pid,
    address _underlying,
    address _collateral,
    uint _amountRepay,
    uint _amountTake
  ) external payable onlyEOA {
    _amountRepay = _capRepay(msg.sender, _pid, _amountRepay);
    _transferIn(_underlying, msg.sender, _amountRepay);
    _repay(msg.sender, _pid, _underlying, _collateral, _amountRepay, _amountTake);
    _transferOut(_collateral, msg.sender, _amountTake);
  }
}
