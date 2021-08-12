// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

import 'OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/token/ERC20/utils/SafeERC20.sol';
import '../BetaBank.sol';

contract MockSameBlockTxTester {
  using SafeERC20 for IERC20;

  BetaBank public immutable betaBank;
  address public immutable utoken;
  address public immutable ctoken;
  uint public pid;

  constructor(
    BetaBank _betaBank,
    address _utoken,
    address _ctoken
  ) {
    IERC20(_utoken).safeApprove(_betaBank.bTokens(_utoken), type(uint).max);
    IERC20(_ctoken).safeApprove(address(_betaBank), type(uint).max);
    betaBank = _betaBank;
    utoken = _utoken;
    ctoken = _ctoken;
  }

  function init(uint _amountPut, uint _amountBorrow) external {
    pid = betaBank.open(address(this), utoken, ctoken);
    betaBank.put(address(this), pid, _amountPut);
    betaBank.borrow(address(this), pid, _amountBorrow);
  }

  function borrowTake(uint _amount) external {
    betaBank.borrow(address(this), pid, _amount);
    betaBank.put(address(this), pid, _amount);
    betaBank.take(address(this), pid, _amount);
  }

  function borrowRepay(uint _amount) external {
    betaBank.borrow(address(this), pid, _amount);
    betaBank.repay(address(this), pid, _amount);
  }

  function putRepay(uint _amount) external {
    betaBank.put(address(this), pid, _amount);
    betaBank.repay(address(this), pid, _amount);
  }

  function putTake(uint _amount) external {
    betaBank.put(address(this), pid, _amount);
    betaBank.take(address(this), pid, _amount);
  }

  function takeBorrow(uint _amount) external {
    betaBank.take(address(this), pid, _amount);
    betaBank.borrow(address(this), pid, _amount);
  }

  function repayBorrow(uint _amount) external {
    betaBank.repay(address(this), pid, _amount);
    betaBank.borrow(address(this), pid, _amount);
  }

  function repayPut(uint _amount) external {
    betaBank.repay(address(this), pid, _amount);
    betaBank.put(address(this), pid, _amount);
  }

  function takePut(uint _amount) external {
    betaBank.take(address(this), pid, _amount);
    betaBank.put(address(this), pid, _amount);
  }
}
