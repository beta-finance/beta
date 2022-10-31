// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

import 'OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/utils/math/Math.sol';
import 'OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/access/Ownable.sol';

import '../interfaces/IBetaInterestModel.sol';

contract BetaDynamicInterestRateModel is IBetaInterestModel, Ownable {
  mapping(address => Config) public configs; // Mapping from BToken address to configs

  struct Config {
    uint96 adjustRate; // How much can interest rate change per day (multiplied by 1e18)
    uint16 loOptUtilRate; // Lower optimal util rate in bps (10_000 = 100%)
    uint16 hiOptUtilRate; // Higher optimal util rate in bps (10_000 = 100%)
    uint96 maxMult; // Max value for interest rate multiplier (multiplied by 1e18)
    uint16 optUtilInterestRate; // Base interest rate at optimal util in bps
    uint16 maxUtilInterestRate; // Base interest rate at max util in bps
  }

  /// @dev Sets configs for bTokens. Can only be called by owner
  /// @param bTokens List of bToken addresses to set configs for
  /// @param _configs List of configurations to set for each bToken
  function setConfigs(address[] calldata bTokens, Config[] calldata _configs) external onlyOwner {
    require(bTokens.length == _configs.length, 'length mismatched');
    for (uint i = 0; i < bTokens.length; ++i) {
      require(
        _configs[i].adjustRate <= 100e18,
        'adjust rate should be in range 0-100e18 (+0% - +10_000% per day)'
      );
      require(
        0 < _configs[i].loOptUtilRate &&
          _configs[i].loOptUtilRate <= _configs[i].hiOptUtilRate &&
          _configs[i].hiOptUtilRate < 10_000,
        'bad lo/hi optimal util rate'
      );
      require(1e18 <= _configs[i].maxMult && _configs[i].maxMult <= 10e18, 'bad max mult');
      require(
        0 < _configs[i].optUtilInterestRate &&
          _configs[i].optUtilInterestRate <= _configs[i].maxUtilInterestRate &&
          _configs[i].maxUtilInterestRate < 50_000,
        'bad opt/max util interest rate'
      );
      configs[bTokens[i]] = _configs[i];
    }
  }

  function initialRate() external view override returns (uint) {
    return 0;
  }

  /// @dev Core logic to get the next interest rate
  function _getNextInterestRate(
    uint prevRate,
    uint totalAvailable,
    uint totalLoan,
    uint timePassed,
    address caller
  ) internal view returns (uint) {
    uint totalLiquidity = totalAvailable + totalLoan;
    if (totalLiquidity == 0) {
      return prevRate;
    }
    uint utilRate = (totalLoan * 1e18) / totalLiquidity;
    Config memory config = configs[caller];
    require(config.maxUtilInterestRate != 0, 'config not found');
    uint multRate;
    uint curRate;
    if (utilRate < uint(config.loOptUtilRate) * 1e14) {
      multRate = 1e36 / (1e18 + (uint(config.adjustRate) * timePassed) / 1 days);
      curRate = _getRatioedY(
        0,
        uint(config.loOptUtilRate) * 1e14,
        0,
        uint(config.optUtilInterestRate) * 1e14,
        utilRate
      );
    } else if (utilRate < uint(config.hiOptUtilRate) * 1e14) {
      multRate = 1e18;
      curRate = uint(config.optUtilInterestRate) * 1e14;
    } else {
      multRate = 1e18 + (uint(config.adjustRate) * timePassed) / 1 days;
      curRate = _getRatioedY(
        uint(config.hiOptUtilRate) * 1e14,
        1e18,
        uint(config.optUtilInterestRate) * 1e14,
        uint(config.maxUtilInterestRate) * 1e14,
        utilRate
      );
    }
    uint targetRate = (prevRate * multRate) / 1e18;

    uint minRate = (curRate * 1e18) / config.maxMult;
    uint maxRate = (curRate * config.maxMult) / 1e18;

    return Math.min(Math.max(targetRate, minRate), maxRate);
  }

  /// @dev Returns the next interest rate for the market.
  /// @param prevRate The current interest rate.
  /// @param totalAvailable The current available liquidity.
  /// @param totalLoan The current total outstanding loans.
  /// @param timePassed The time passed since last interest rate rebase in seconds.
  function getNextInterestRate(
    uint prevRate,
    uint totalAvailable,
    uint totalLoan,
    uint timePassed
  ) external view override returns (uint) {
    return _getNextInterestRate(prevRate, totalAvailable, totalLoan, timePassed, msg.sender);
  }

  /// @dev Compute the corresponding value for y given the value x on the line from point (minX, minY) to (maxX, maxY)
  /// @param minX Starting x-value
  /// @param maxX Ending x-value
  /// @param minY Starting y-value
  /// @param maxY Ending y-value
  /// @param x Current x-value to get the corresponding y-value
  /// @notice Requirements: minX <= x <= maxX , minY < maxY, minX < maxX
  function _getRatioedY(
    uint minX,
    uint maxX,
    uint minY,
    uint maxY,
    uint x
  ) internal pure returns (uint) {
    return minY + ((maxY - minY) * (x - minX)) / (maxX - minX);
  }
}
