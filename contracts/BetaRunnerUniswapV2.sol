// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

import 'OpenZeppelin/openzeppelin-contracts@4.0.0/contracts/token/ERC20/utils/SafeERC20.sol';

import './BetaRunnerBase.sol';
import './BetaRunnerWithCallback.sol';
import './libraries/SafeCast.sol';
import '../interfaces/IUniswapV2Pair.sol';
import '../interfaces/IUniswapV2Callee.sol';
import '../interfaces/IPancakeCallee.sol';

contract BetaRunnerUniswapV2 is
  BetaRunnerBase,
  BetaRunnerWithCallback,
  IUniswapV2Callee,
  IPancakeCallee
{
  using SafeCast for uint;
  using SafeERC20 for IERC20;

  address public immutable factory;
  bytes32 public immutable codeHash;

  constructor(
    address _betaBank,
    address _weth,
    address _factory,
    bytes32 _codeHash
  ) BetaRunnerBase(_betaBank, _weth) {
    factory = _factory;
    codeHash = _codeHash;
  }

  struct CallbackData {
    uint pid;
    int memo; // positive if short (extra collateral) | negative if close (amount to take)
    address[] path;
    uint[] amounts;
  }

  function short(
    uint _pid,
    uint _amountBorrow,
    uint _amountPutExtra,
    address[] memory _path,
    uint _amountOutMin
  ) external payable onlyEOA withCallback {
    _transferIn(_path[_path.length - 1], msg.sender, _amountPutExtra);
    uint[] memory amounts = _getAmountsOut(_amountBorrow, _path);
    require(amounts[amounts.length - 1] >= _amountOutMin, 'short/not-enough-out');
    IUniswapV2Pair(_pairFor(_path[0], _path[1])).swap(
      _path[0] < _path[1] ? 0 : amounts[1],
      _path[0] < _path[1] ? amounts[1] : 0,
      address(this),
      abi.encode(
        CallbackData({pid: _pid, memo: _amountPutExtra.toInt256(), path: _path, amounts: amounts})
      )
    );
  }

  function close(
    uint _pid,
    uint _amountRepay,
    uint _amountTake,
    address[] memory _path,
    uint _amountInMax
  ) external payable onlyEOA withCallback {
    _amountRepay = _capRepay(msg.sender, _pid, _amountRepay);
    uint[] memory amounts = _getAmountsIn(_amountRepay, _path);
    require(amounts[0] <= _amountInMax, 'close/too-much-in');
    IUniswapV2Pair(_pairFor(_path[0], _path[1])).swap(
      _path[0] < _path[1] ? 0 : amounts[1],
      _path[0] < _path[1] ? amounts[1] : 0,
      address(this),
      abi.encode(
        CallbackData({pid: _pid, memo: -_amountTake.toInt256(), path: _path, amounts: amounts})
      )
    );
  }

  /// @dev Continues the action (uniswap / sushiswap)
  function uniswapV2Call(
    address sender,
    uint,
    uint,
    bytes calldata data
  ) external override isCallback {
    require(sender == address(this), 'uniswapV2Call/bad-sender');
    _pairCallback(data);
  }

  /// @dev Continues the action (pancakeswap)
  function pancakeCall(
    address sender,
    uint,
    uint,
    bytes calldata data
  ) external override isCallback {
    require(sender == address(this), 'pancakeCall/bad-sender');
    _pairCallback(data);
  }

  /// @dev Continues the action (uniswap / sushiswap / pancakeswap)
  function _pairCallback(bytes calldata data) internal {
    CallbackData memory cb = abi.decode(data, (CallbackData));
    require(msg.sender == _pairFor(cb.path[0], cb.path[1]), '_pairCallback/bad-caller');
    uint len = cb.path.length;
    if (len > 2) {
      address pair = _pairFor(cb.path[1], cb.path[2]);
      IERC20(cb.path[1]).safeTransfer(pair, cb.amounts[1]);
      for (uint idx = 1; idx < len - 1; idx++) {
        (address input, address output) = (cb.path[idx], cb.path[idx + 1]);
        address to = idx < len - 2 ? _pairFor(output, cb.path[idx + 2]) : address(this);
        uint amount0Out = input < output ? 0 : cb.amounts[idx + 1];
        uint amount1Out = input < output ? cb.amounts[idx + 1] : 0;
        IUniswapV2Pair(pair).swap(amount0Out, amount1Out, to, new bytes(0));
        pair = to;
      }
    }
    if (cb.memo > 0) {
      uint amountCollateral = uint(cb.memo);
      (address und, address col) = (cb.path[0], cb.path[len - 1]);
      _borrow(tx.origin, cb.pid, und, col, cb.amounts[0], cb.amounts[len - 1] + amountCollateral);
      IERC20(und).safeTransfer(msg.sender, cb.amounts[0]);
    } else {
      uint amountTake = uint(-cb.memo);
      (address und, address col) = (cb.path[len - 1], cb.path[0]);
      _repay(tx.origin, cb.pid, und, col, cb.amounts[len - 1], amountTake);
      IERC20(col).safeTransfer(msg.sender, cb.amounts[0]);
      _transferOut(col, tx.origin, IERC20(col).balanceOf(address(this)));
    }
  }

  /// Internal UniswapV2 library functions
  /// See https://github.com/Uniswap/uniswap-v2-periphery/blob/master/contracts/libraries/UniswapV2Library.sol
  function _sortTokens(address tokenA, address tokenB)
    internal
    pure
    returns (address token0, address token1)
  {
    require(tokenA != tokenB, 'IDENTICAL_ADDRESSES');
    (token0, token1) = tokenA < tokenB ? (tokenA, tokenB) : (tokenB, tokenA);
    require(token0 != address(0), 'ZERO_ADDRESS');
  }

  function _pairFor(address tokenA, address tokenB) internal view returns (address) {
    (address token0, address token1) = _sortTokens(tokenA, tokenB);
    bytes32 salt = keccak256(abi.encodePacked(token0, token1));
    return address(uint160(uint(keccak256(abi.encodePacked(hex'ff', factory, salt, codeHash)))));
  }

  function _getReserves(address tokenA, address tokenB)
    internal
    view
    returns (uint reserveA, uint reserveB)
  {
    (address token0, ) = _sortTokens(tokenA, tokenB);
    (uint reserve0, uint reserve1, ) = IUniswapV2Pair(_pairFor(tokenA, tokenB)).getReserves();
    (reserveA, reserveB) = tokenA == token0 ? (reserve0, reserve1) : (reserve1, reserve0);
  }

  function _getAmountOut(
    uint amountIn,
    uint reserveIn,
    uint reserveOut
  ) internal pure returns (uint amountOut) {
    require(amountIn > 0, 'INSUFFICIENT_INPUT_AMOUNT');
    require(reserveIn > 0 && reserveOut > 0, 'INSUFFICIENT_LIQUIDITY');
    uint amountInWithFee = amountIn * 997;
    uint numerator = amountInWithFee * reserveOut;
    uint denominator = (reserveIn * 1000) + amountInWithFee;
    amountOut = numerator / denominator;
  }

  function _getAmountIn(
    uint amountOut,
    uint reserveIn,
    uint reserveOut
  ) internal pure returns (uint amountIn) {
    require(amountOut > 0, 'INSUFFICIENT_OUTPUT_AMOUNT');
    require(reserveIn > 0 && reserveOut > 0, 'INSUFFICIENT_LIQUIDITY');
    uint numerator = reserveIn * amountOut * 1000;
    uint denominator = (reserveOut - amountOut) * 997;
    amountIn = (numerator / denominator) + 1;
  }

  function _getAmountsOut(uint amountIn, address[] memory path)
    internal
    view
    returns (uint[] memory amounts)
  {
    require(path.length >= 2, 'INVALID_PATH');
    amounts = new uint[](path.length);
    amounts[0] = amountIn;
    for (uint i; i < path.length - 1; i++) {
      (uint reserveIn, uint reserveOut) = _getReserves(path[i], path[i + 1]);
      amounts[i + 1] = _getAmountOut(amounts[i], reserveIn, reserveOut);
    }
  }

  function _getAmountsIn(uint amountOut, address[] memory path)
    internal
    view
    returns (uint[] memory amounts)
  {
    require(path.length >= 2, 'INVALID_PATH');
    amounts = new uint[](path.length);
    amounts[amounts.length - 1] = amountOut;
    for (uint i = path.length - 1; i > 0; i--) {
      (uint reserveIn, uint reserveOut) = _getReserves(path[i - 1], path[i]);
      amounts[i - 1] = _getAmountIn(amounts[i], reserveIn, reserveOut);
    }
  }
}
