// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

import '../interfaces/IBetaConfig.sol';

contract BetaConfig is IBetaConfig {
  struct RiskConfig {
    uint64 safetyLTV;
    uint64 liquidationLTV;
    uint64 killBountyRate;
  }

  event SetGovernor(address governor);
  event SetPendingGovernor(address pendingGovernor);
  event SetCollFactor(address indexed token, uint factor);
  event SetRiskLevel(address indexed token, uint level);
  event SetRiskConfig(
    uint indexed level,
    uint64 safetyLTV,
    uint64 liquidationLTV,
    uint64 killBountyRate
  );
  event SetReserveInfo(address indexed beneficiary, uint rate);

  address public governor;
  address public pendingGovernor;
  address public override reserveBeneficiary;
  uint public override reserveRate;

  mapping(address => uint) public cFactors; // collateral factors
  mapping(address => uint) public rLevels; // risk levels
  mapping(uint => RiskConfig) public rConfigs; // risk configurations

  constructor(address _reserveBeneficiary, uint _reserveRate) {
    governor = msg.sender;
    emit SetGovernor(msg.sender);
    setReserveInfo(_reserveBeneficiary, _reserveRate);
  }

  /// @dev Sets the next governor, which will be in effect when they accept.
  /// @param _pendingGovernor The next governor address.
  function setPendingGovernor(address _pendingGovernor) external {
    require(msg.sender == governor, 'setPendingGovernor/not-governor');
    pendingGovernor = _pendingGovernor;
    emit SetPendingGovernor(_pendingGovernor);
  }

  /// @dev Accepts to become the next governor. Must only be called by the pending governor.
  function acceptGovernor() external {
    require(msg.sender == pendingGovernor, 'acceptGovernor/not-pending-governor');
    pendingGovernor = address(0);
    governor = msg.sender;
    emit SetGovernor(msg.sender);
  }

  /// @dev Updates collateral factors of the given tokens.
  function setCollFactors(address[] calldata tokens, uint[] calldata factors) external {
    require(msg.sender == governor, 'setCollFactors/not-governor');
    require(tokens.length == factors.length, 'setCollFactors/bad-length');
    for (uint idx = 0; idx < tokens.length; idx++) {
      require(factors[idx] <= 1e18, 'setCollFactors/bad-factor-value');
      cFactors[tokens[idx]] = factors[idx];
      emit SetCollFactor(tokens[idx], factors[idx]);
    }
  }

  /// @dev Sets the risk levels of the given tokens.
  function setRiskLevels(address[] calldata tokens, uint[] calldata levels) external {
    require(msg.sender == governor, 'setRiskLevels/not-governor');
    require(tokens.length == levels.length, 'setRiskLevels/bad-length');
    for (uint idx = 0; idx < tokens.length; idx++) {
      rLevels[tokens[idx]] = levels[idx];
      emit SetRiskLevel(tokens[idx], levels[idx]);
    }
  }

  /// @dev Sets the risk configurations of the given levels.
  function setRiskConfigs(uint[] calldata levels, RiskConfig[] calldata configs) external {
    require(msg.sender == governor, 'setRiskConfigs/not-governor');
    require(levels.length == configs.length, 'setRiskConfigs/bad-length');
    for (uint idx = 0; idx < levels.length; idx++) {
      require(configs[idx].safetyLTV <= 1e18, 'setRiskConfigs/bad-safety-ltv');
      require(configs[idx].liquidationLTV <= 1e18, 'setRiskConfigs/bad-liquidation-ltv');
      require(
        configs[idx].safetyLTV < configs[idx].liquidationLTV,
        'setRiskConfigs/inconsistent-ltv-values'
      );
      require(configs[idx].killBountyRate <= 1e18, 'setRiskConfigs/bad-kill-reward-factor');
      rConfigs[levels[idx]] = configs[idx];
      emit SetRiskConfig(
        levels[idx],
        configs[idx].safetyLTV,
        configs[idx].liquidationLTV,
        configs[idx].killBountyRate
      );
    }
  }

  /// @dev Sets the global reserve information.
  function setReserveInfo(address _reserveBeneficiary, uint _reserveRate) public {
    require(msg.sender == governor, 'setReserveInfo/not-governor');
    require(_reserveRate < 1e18, 'setReserveInfo/bad-rate');
    require(_reserveBeneficiary != address(0), 'setReserveInfo/bad-beneficiary');
    reserveBeneficiary = _reserveBeneficiary;
    reserveRate = _reserveRate;
    emit SetReserveInfo(_reserveBeneficiary, _reserveRate);
  }

  /// @dev Returns the collateral factor of the given token. Must be greater than zero.
  function getCollFactor(address _token) external view override returns (uint) {
    uint factor = cFactors[_token];
    require(factor > 0, 'getCollFactor/no-collateral-factor');
    return factor;
  }

  /// @dev Returns the risk level of the given token. Zero is the default value of all tokens.
  function getRiskLevel(address _token) public view override returns (uint) {
    uint level = rLevels[_token];
    require(level != type(uint).max, 'getRiskLevel/bad-risk-level');
    return level;
  }

  /// @dev Returns the safety LTV of the given token. Must be greater than zero.
  function getSafetyLTV(address _token) external view override returns (uint) {
    uint ltv = rConfigs[getRiskLevel(_token)].safetyLTV;
    require(ltv > 0, 'getSafetyLTV/no-ltv');
    return ltv;
  }

  /// @dev Returns the liquidation LTV of the given token. Must be greater than zero.
  function getLiquidationLTV(address _token) external view override returns (uint) {
    uint ltv = rConfigs[getRiskLevel(_token)].liquidationLTV;
    require(ltv > 0, 'getLiquidationLTV/no-ltv');
    return ltv;
  }

  /// @dev Returns the kill bounty rate of the given token. Must be greater than zero.
  function getKillBountyRate(address _token) external view override returns (uint) {
    uint rate = rConfigs[getRiskLevel(_token)].killBountyRate;
    require(rate > 0, 'getKillBountyRate/no-rate');
    return rate;
  }
}
