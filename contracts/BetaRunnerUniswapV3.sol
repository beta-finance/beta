// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

import 'OpenZeppelin/openzeppelin-contracts@4.0.0/contracts/token/ERC20/utils/SafeERC20.sol';

import './BetaRunnerBase.sol';
import './BetaRunnerWithCallback.sol';
import './libraries/Path.sol';
import './libraries/SafeCast.sol';
import '../interfaces/IUniswapV3Pool.sol';
import '../interfaces/IUniswapV3SwapCallback.sol';

contract BetaRunnerUniswapV3 is BetaRunnerBase, BetaRunnerWithCallback, IUniswapV3SwapCallback {
  using SafeERC20 for IERC20;
  using Path for bytes;
  using SafeCast for uint;

  /// @dev Constants from Uniswap V3 to be used for swap
  /// (https://github.com/Uniswap/uniswap-v3-core/blob/main/contracts/libraries/TickMath.sol)
  uint160 internal constant MIN_SQRT_RATIO = 4295128739;
  uint160 internal constant MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342;

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

  struct ShortData {
    uint pid;
    uint amountBorrow;
    uint amountPutExtra;
    bytes path;
    uint amountOutMin;
  }

  struct CloseData {
    uint pid;
    uint amountRepay;
    uint amountTake;
    bytes path;
    uint amountInMax;
  }

  struct CallbackData {
    uint pid;
    address path0;
    uint amount0;
    int memo; // positive if short (extra collateral) | negative if close (amount to take)
    bytes path;
  }

  /// @dev Borrows the asset using the given collateral, and swaps it using the given path.
  function short(ShortData calldata _data) external payable onlyEOA withCallback {
    (, address collateral, ) = _data.path.decodeLastPool();
    _transferIn(collateral, msg.sender, _data.amountPutExtra);
    (address tokenIn, address tokenOut, uint24 fee) = _data.path.decodeFirstPool();
    bool zeroForOne = tokenIn < tokenOut;
    CallbackData memory cb =
      CallbackData({
        pid: _data.pid,
        path0: tokenIn,
        amount0: _data.amountBorrow,
        memo: _data.amountPutExtra.toInt256(),
        path: _data.path
      });
    (int amount0, int amount1) =
      IUniswapV3Pool(_poolFor(tokenIn, tokenOut, fee)).swap(
        address(this),
        zeroForOne,
        _data.amountBorrow.toInt256(),
        zeroForOne ? MIN_SQRT_RATIO + 1 : MAX_SQRT_RATIO - 1,
        abi.encode(cb)
      );
    uint amountReceived = amount0 > 0 ? uint(-amount1) : uint(-amount0);
    require(amountReceived >= _data.amountOutMin, '!slippage');
  }

  /// @dev Swaps the collateral to the underlying asset using the given path, and repays it to the pool.
  function close(CloseData calldata _data) external payable onlyEOA withCallback {
    uint amountRepay = _capRepay(msg.sender, _data.pid, _data.amountRepay);
    (address tokenOut, address tokenIn, uint24 fee) = _data.path.decodeFirstPool();
    bool zeroForOne = tokenIn < tokenOut;
    CallbackData memory cb =
      CallbackData({
        pid: _data.pid,
        path0: tokenOut,
        amount0: amountRepay,
        memo: -_data.amountTake.toInt256(),
        path: _data.path
      });
    (int amount0, int amount1) =
      IUniswapV3Pool(_poolFor(tokenIn, tokenOut, fee)).swap(
        address(this),
        zeroForOne,
        -amountRepay.toInt256(),
        zeroForOne ? MIN_SQRT_RATIO + 1 : MAX_SQRT_RATIO - 1,
        abi.encode(cb)
      );
    uint amountPaid = amount0 > 0 ? uint(amount0) : uint(amount1);
    require(amountPaid <= _data.amountInMax, '!slippage');
  }

  /// @dev Continues the action through uniswapv3
  function uniswapV3SwapCallback(
    int _amount0Delta,
    int _amount1Delta,
    bytes calldata _data
  ) external override isCallback {
    CallbackData memory data = abi.decode(_data, (CallbackData));
    (uint amountToPay, uint amountReceived) =
      _amount0Delta > 0
        ? (uint(_amount0Delta), uint(-_amount1Delta))
        : (uint(_amount1Delta), uint(-_amount0Delta));
    if (data.memo > 0) {
      _shortCallback(amountToPay, amountReceived, data);
    } else {
      _closeCallback(amountToPay, amountReceived, data);
    }
  }

  function _shortCallback(
    uint _amountToPay,
    uint _amountReceived,
    CallbackData memory data
  ) internal {
    (address tokenIn, address tokenOut, uint24 prevFee) = data.path.decodeFirstPool();
    require(msg.sender == _poolFor(tokenIn, tokenOut, prevFee), '_shortCallback/bad-caller');
    if (data.path.hasMultiplePools()) {
      data.path = data.path.skipToken();
      (, address tokenNext, uint24 fee) = data.path.decodeFirstPool();
      bool zeroForOne = tokenOut < tokenNext;
      IUniswapV3Pool(_poolFor(tokenOut, tokenNext, fee)).swap(
        address(this),
        zeroForOne,
        _amountReceived.toInt256(),
        zeroForOne ? MIN_SQRT_RATIO + 1 : MAX_SQRT_RATIO - 1,
        abi.encode(data)
      );
    } else {
      uint amountPut = _amountReceived + uint(data.memo);
      _borrow(tx.origin, data.pid, data.path0, tokenOut, data.amount0, amountPut);
    }
    IERC20(tokenIn).safeTransfer(msg.sender, _amountToPay);
  }

  function _closeCallback(
    uint _amountToPay,
    uint,
    CallbackData memory data
  ) internal {
    (address tokenOut, address tokenIn, uint24 prevFee) = data.path.decodeFirstPool();
    require(msg.sender == _poolFor(tokenIn, tokenOut, prevFee), '_closeCallback/bad-caller');
    if (data.path.hasMultiplePools()) {
      data.path = data.path.skipToken();
      (, address tokenNext, uint24 fee) = data.path.decodeFirstPool();
      bool zeroForOne = tokenNext < tokenIn;
      IUniswapV3Pool(_poolFor(tokenIn, tokenNext, fee)).swap(
        msg.sender,
        zeroForOne,
        -_amountToPay.toInt256(),
        zeroForOne ? MIN_SQRT_RATIO + 1 : MAX_SQRT_RATIO - 1,
        abi.encode(data)
      );
    } else {
      uint amountTake = uint(-data.memo);
      _repay(tx.origin, data.pid, data.path0, tokenIn, data.amount0, amountTake);
      IERC20(tokenIn).safeTransfer(msg.sender, _amountToPay);
      _transferOut(tokenIn, tx.origin, IERC20(tokenIn).balanceOf(address(this)));
    }
  }

  function _poolFor(
    address tokenA,
    address tokenB,
    uint24 fee
  ) internal view returns (address) {
    (address token0, address token1) = tokenA < tokenB ? (tokenA, tokenB) : (tokenB, tokenA);
    bytes32 salt = keccak256(abi.encode(token0, token1, fee));
    return address(uint160(uint(keccak256(abi.encodePacked(hex'ff', factory, salt, codeHash)))));
  }
}
