// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

import 'OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/token/ERC20/IERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/token/ERC20/utils/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/proxy/utils/Initializable.sol';
import 'OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/security/Pausable.sol';
import 'OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/utils/Address.sol';
import 'OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/utils/math/Math.sol';

import './BToken.sol';
import './BTokenDeployer.sol';
import '../interfaces/IBetaBank.sol';
import '../interfaces/IBetaOracle.sol';

contract BetaBank is IBetaBank, Initializable, Pausable {
  using Address for address;
  using SafeERC20 for IERC20;

  event Create(address indexed underlying, address bToken);
  event Open(address indexed owner, uint indexed pid, address bToken, address collateral);
  event Borrow(address indexed owner, uint indexed pid, uint amount, uint share, address borrower);
  event Repay(address indexed owner, uint indexed pid, uint amount, uint share, address payer);
  event Put(address indexed owner, uint indexed pid, uint amount, address payer);
  event Take(address indexed owner, uint indexed pid, uint amount, address to);
  event Liquidate(
    address indexed owner,
    uint indexed pid,
    uint amount,
    uint share,
    uint reward,
    address caller
  );
  event SelflessLiquidate(
    address indexed owner,
    uint indexed pid,
    uint amount,
    uint share,
    address caller
  );
  event SetGovernor(address governor);
  event SetPendingGovernor(address pendingGovernor);
  event SetOracle(address oracle);
  event SetConfig(address config);
  event SetInterestModel(address interestModel);
  event SetRunnerWhitelist(address indexed runner, bool ok);
  event SetOwnerWhitelist(address indexed owner, bool ok);
  event SetAllowPublicCreate(bool ok);

  struct Position {
    uint32 blockBorrowPut; // safety check
    uint32 blockRepayTake; // safety check
    address bToken;
    address collateral;
    uint collateralSize;
    uint debtShare;
  }

  uint private unlocked; // reentrancy variable
  address public deployer; // deployer address
  address public override oracle; // oracle address
  address public override config; // config address
  address public override interestModel; // interest rate model address
  address public governor; // current governor
  address public pendingGovernor; // pending governor
  bool public allowPublicCreate; // allow public to create pool status

  mapping(address => address) public override bTokens; // mapping from underlying to bToken
  mapping(address => address) public override underlyings; // mapping from bToken to underlying token
  mapping(address => bool) public runnerWhitelists; // whitelist of authorized routers
  mapping(address => bool) public ownerWhitelists; // whitelist of authorized owners

  mapping(address => mapping(uint => Position)) public positions; // mapping from user to pool id to Position info
  mapping(address => uint) public nextPositionIds; // mapping from user to next position id (position count)

  /// @dev Reentrancy guard modifier
  modifier lock() {
    require(unlocked == 1, 'BetaBank/locked');
    unlocked = 2;
    _;
    unlocked = 1;
  }

  /// @dev Only governor is allowed modifier.
  modifier onlyGov() {
    require(msg.sender == governor, 'BetaBank/onlyGov');
    _;
  }

  /// @dev Check if sender is allowed to perform action on behalf of the owner modifier.
  modifier isPermittedByOwner(address _owner) {
    require(isPermittedCaller(_owner, msg.sender), 'BetaBank/isPermittedByOwner');
    _;
  }

  /// @dev Check is pool id exist for the owner modifier.
  modifier checkPID(address _owner, uint _pid) {
    require(_pid < nextPositionIds[_owner], 'BetaBank/checkPID');
    _;
  }

  /// @dev Initializes this smart contract. No constructor to make this upgradable.
  function initialize(
    address _governor,
    address _deployer,
    address _oracle,
    address _config,
    address _interestModel
  ) external initializer {
    require(_governor != address(0), 'initialize/governor-zero-address');
    require(_deployer != address(0), 'initialize/deployer-zero-address');
    require(_oracle != address(0), 'initialize/oracle-zero-address');
    require(_config != address(0), 'initialize/config-zero-address');
    require(_interestModel != address(0), 'initialize/interest-model-zero-address');
    governor = _governor;
    deployer = _deployer;
    oracle = _oracle;
    config = _config;
    interestModel = _interestModel;
    unlocked = 1;
    emit SetGovernor(_governor);
    emit SetOracle(_oracle);
    emit SetConfig(_config);
    emit SetInterestModel(_interestModel);
  }

  /// @dev Sets the next governor, which will be in effect when they accept.
  /// @param _pendingGovernor The next governor address.
  function setPendingGovernor(address _pendingGovernor) external onlyGov {
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

  /// @dev Updates the oracle address. Must only be called by the governor.
  function setOracle(address _oracle) external onlyGov {
    require(_oracle != address(0), 'setOracle/zero-address');
    oracle = _oracle;
    emit SetOracle(_oracle);
  }

  /// @dev Updates the config address. Must only be called by the governor.
  function setConfig(address _config) external onlyGov {
    require(_config != address(0), 'setConfig/zero-address');
    config = _config;
    emit SetConfig(_config);
  }

  /// @dev Updates the interest model address. Must only be called by the governor.
  function setInterestModel(address _interestModel) external onlyGov {
    require(_interestModel != address(0), 'setInterestModel/zero-address');
    interestModel = _interestModel;
    emit SetInterestModel(_interestModel);
  }

  /// @dev Sets the whitelist statuses for the given runners. Must only be called by the governor.
  function setRunnerWhitelists(address[] calldata _runners, bool ok) external onlyGov {
    for (uint idx = 0; idx < _runners.length; idx++) {
      runnerWhitelists[_runners[idx]] = ok;
      emit SetRunnerWhitelist(_runners[idx], ok);
    }
  }

  /// @dev Sets the whitelist statuses for the given owners. Must only be called by the governor.
  function setOwnerWhitelists(address[] calldata _owners, bool ok) external onlyGov {
    for (uint idx = 0; idx < _owners.length; idx++) {
      ownerWhitelists[_owners[idx]] = ok;
      emit SetOwnerWhitelist(_owners[idx], ok);
    }
  }

  /// @dev Pauses and stops money market-related interactions. Must only be called by the governor.
  function pause() external whenNotPaused onlyGov {
    _pause();
  }

  /// @dev Unpauses and allows again money market-related interactions. Must only be called by the governor.
  function unpause() external whenPaused onlyGov {
    _unpause();
  }

  /// @dev Sets whether anyone can create btoken of any token. Must only be called by the governor.
  function setAllowPublicCreate(bool _ok) external onlyGov {
    allowPublicCreate = _ok;
    emit SetAllowPublicCreate(_ok);
  }

  /// @dev Creates a new money market for the given underlying token. Permissionless.
  /// @param _underlying The ERC-20 that is borrowable in the newly created market contract.
  function create(address _underlying) external lock whenNotPaused returns (address bToken) {
    require(allowPublicCreate || msg.sender == governor, 'create/unauthorized');
    require(_underlying != address(this), 'create/not-like-this');
    require(_underlying.isContract(), 'create/underlying-not-contract');
    require(bTokens[_underlying] == address(0), 'create/underlying-already-exists');
    require(IBetaOracle(oracle).getAssetETHPrice(_underlying) > 0, 'create/no-price');
    bToken = BTokenDeployer(deployer).deploy(_underlying);
    bTokens[_underlying] = bToken;
    underlyings[bToken] = _underlying;
    emit Create(_underlying, bToken);
  }

  /// @dev Returns whether the given sender is allowed to interact with a position of the owner.
  function isPermittedCaller(address _owner, address _sender) public view returns (bool) {
    // ONE OF THE TWO CONDITIONS MUST HOLD:
    // 1. allow if sender is owner and owner is whitelisted.
    // 2. allow if owner is origin tx sender (for extra safety) and sender is globally accepted.
    return ((_owner == _sender && ownerWhitelists[_owner]) ||
      (_owner == tx.origin && runnerWhitelists[_sender]));
  }

  /// @dev Returns the position's collateral token and BToken.
  function getPositionTokens(address _owner, uint _pid)
    external
    view
    override
    checkPID(_owner, _pid)
    returns (address _collateral, address _bToken)
  {
    Position storage pos = positions[_owner][_pid];
    _collateral = pos.collateral;
    _bToken = pos.bToken;
  }

  /// @dev Returns the debt of the given position. Can't be view as it needs to call accrue.
  function fetchPositionDebt(address _owner, uint _pid)
    external
    override
    checkPID(_owner, _pid)
    returns (uint)
  {
    Position storage pos = positions[_owner][_pid];
    return BToken(pos.bToken).fetchDebtShareValue(pos.debtShare);
  }

  /// @dev Returns the LTV of the given position. Can't be view as it needs to call accrue.
  function fetchPositionLTV(address _owner, uint _pid)
    external
    override
    checkPID(_owner, _pid)
    returns (uint)
  {
    return _fetchPositionLTV(positions[_owner][_pid]);
  }

  /// @dev Opens a new position to borrow a specific token for a specific collateral.
  /// @param _owner The owner of the newly created position. Sender must be allowed to act for.
  /// @param _underlying The token that is allowed to be borrowed in this position.
  /// @param _collateral The token that is used as collateral in this position.
  function open(
    address _owner,
    address _underlying,
    address _collateral
  ) external override whenNotPaused isPermittedByOwner(_owner) returns (uint pid) {
    address bToken = bTokens[_underlying];
    require(bToken != address(0), 'open/bad-underlying');
    require(_underlying != _collateral, 'open/self-collateral');
    require(IBetaConfig(config).getCollFactor(_collateral) > 0, 'open/bad-collateral');
    require(IBetaOracle(oracle).getAssetETHPrice(_collateral) > 0, 'open/no-price');
    pid = nextPositionIds[_owner]++;
    Position storage pos = positions[_owner][pid];
    pos.bToken = bToken;
    pos.collateral = _collateral;
    emit Open(_owner, pid, bToken, _collateral);
  }

  /// @dev Borrows tokens on the given position. Position must still be safe.
  /// @param _owner The position owner to borrow underlying tokens.
  /// @param _pid The position id to borrow underlying tokens.
  /// @param _amount The amount of underlying tokens to borrow.
  function borrow(
    address _owner,
    uint _pid,
    uint _amount
  ) external override lock whenNotPaused isPermittedByOwner(_owner) checkPID(_owner, _pid) {
    // 1. pre-conditions
    Position memory pos = positions[_owner][_pid];
    require(pos.blockRepayTake != uint32(block.number), 'borrow/bad-block');
    // 2. perform the borrow and update the position
    uint share = BToken(pos.bToken).borrow(msg.sender, _amount);
    pos.debtShare += share;
    positions[_owner][_pid].debtShare = pos.debtShare;
    positions[_owner][_pid].blockBorrowPut = uint32(block.number);
    // 3. make sure the position is still safe
    uint ltv = _fetchPositionLTV(pos);
    require(ltv <= IBetaConfig(config).getSafetyLTV(underlyings[pos.bToken]), 'borrow/not-safe');
    emit Borrow(_owner, _pid, _amount, share, msg.sender);
  }

  /// @dev Repays tokens on the given position. Payer must be position owner or sender.
  /// @param _owner The position owner to repay underlying tokens.
  /// @param _pid The position id to repay underlying tokens.
  /// @param _amount The amount of underlying tokens to repay.
  function repay(
    address _owner,
    uint _pid,
    uint _amount
  ) external override lock whenNotPaused isPermittedByOwner(_owner) checkPID(_owner, _pid) {
    // 1. pre-conditions
    Position memory pos = positions[_owner][_pid];
    require(pos.blockBorrowPut != uint32(block.number), 'repay/bad-block');
    // 2. perform the repayment and update the position - no collateral check required
    uint share = BToken(pos.bToken).repay(msg.sender, _amount);
    pos.debtShare -= share;
    positions[_owner][_pid].debtShare = pos.debtShare;
    positions[_owner][_pid].blockRepayTake = uint32(block.number);
    emit Repay(_owner, _pid, _amount, share, msg.sender);
  }

  /// @dev Puts more collateral to the given position. Payer must be position owner or sender.
  /// @param _owner The position owner to put more collateral.
  /// @param _pid The position id to put more collateral.
  /// @param _amount The amount of collateral to put via `transferFrom`.
  function put(
    address _owner,
    uint _pid,
    uint _amount
  ) external override lock whenNotPaused isPermittedByOwner(_owner) checkPID(_owner, _pid) {
    // 1. pre-conditions
    Position memory pos = positions[_owner][_pid];
    require(pos.blockRepayTake != uint32(block.number), 'put/bad-block');
    // 2. transfer collateral tokens in
    uint amount;
    {
      uint balBefore = IERC20(pos.collateral).balanceOf(address(this));
      IERC20(pos.collateral).safeTransferFrom(msg.sender, address(this), _amount);
      uint balAfter = IERC20(pos.collateral).balanceOf(address(this));
      amount = balAfter - balBefore;
    }
    // 3. update the position - no collateral check required
    pos.collateralSize += amount;
    positions[_owner][_pid].collateralSize = pos.collateralSize;
    positions[_owner][_pid].blockBorrowPut = uint32(block.number);
    emit Put(_owner, _pid, _amount, msg.sender);
  }

  /// @dev Takes some collateral out of the position and send it out. Position must still be safe.
  /// @param _owner The position owner to take collateral out.
  /// @param _pid The position id to take collateral out.
  /// @param _amount The amount of collateral to take via `transfer`.
  function take(
    address _owner,
    uint _pid,
    uint _amount
  ) external override lock whenNotPaused isPermittedByOwner(_owner) checkPID(_owner, _pid) {
    // 1. pre-conditions
    Position memory pos = positions[_owner][_pid];
    require(pos.blockBorrowPut != uint32(block.number), 'take/bad-block');
    // 2. update position collateral size
    pos.collateralSize -= _amount;
    positions[_owner][_pid].collateralSize = pos.collateralSize;
    positions[_owner][_pid].blockRepayTake = uint32(block.number);
    // 3. make sure the position is still safe
    uint ltv = _fetchPositionLTV(pos);
    require(ltv <= IBetaConfig(config).getSafetyLTV(underlyings[pos.bToken]), 'take/not-safe');
    // 4. transfer collateral tokens out
    IERC20(pos.collateral).safeTransfer(msg.sender, _amount);
    emit Take(_owner, _pid, _amount, msg.sender);
  }

  /// @dev Liquidates the given position. Can be called by anyone but must be liquidatable.
  /// @param _owner The position owner to be liquidated.
  /// @param _pid The position id to be liquidated.
  /// @param _amount The amount of debt to be repaid by caller. Must not exceed half debt (rounded up).
  function liquidate(
    address _owner,
    uint _pid,
    uint _amount
  ) external override lock whenNotPaused checkPID(_owner, _pid) {
    // 1. check liquidation condition
    Position memory pos = positions[_owner][_pid];
    address underlying = underlyings[pos.bToken];
    uint ltv = _fetchPositionLTV(pos);
    require(ltv >= IBetaConfig(config).getLiquidationLTV(underlying), 'liquidate/not-liquidatable');
    // 2. perform repayment
    uint debtShare = BToken(pos.bToken).repay(msg.sender, _amount);
    require(debtShare <= (pos.debtShare + 1) / 2, 'liquidate/too-much-liquidation');
    // 3. calculate reward and payout
    uint debtValue = BToken(pos.bToken).fetchDebtShareValue(debtShare);
    uint collValue = IBetaOracle(oracle).convert(underlying, pos.collateral, debtValue);
    uint payout = Math.min(
      collValue + (collValue * IBetaConfig(config).getKillBountyRate(underlying)) / 1e18,
      pos.collateralSize
    );
    // 4. update the position
    pos.debtShare -= debtShare;
    positions[_owner][_pid].debtShare = pos.debtShare;
    pos.collateralSize -= payout;
    positions[_owner][_pid].collateralSize = pos.collateralSize;
    // 5. transfer the payout out
    IERC20(pos.collateral).safeTransfer(msg.sender, payout);
    emit Liquidate(_owner, _pid, _amount, debtShare, payout, msg.sender);
  }

  /// @dev onlyGov selfless liquidation if collateral size = 0
  /// @param _owner The position owner to be liquidated.
  /// @param _pid The position id to be liquidated.
  /// @param _amount The amount of debt to be repaid by caller.
  function selflessLiquidate(
    address _owner,
    uint _pid,
    uint _amount
  ) external onlyGov lock checkPID(_owner, _pid) {
    // 1. check positions collateral size
    Position memory pos = positions[_owner][_pid];
    require(pos.collateralSize == 0, 'selflessLiquidate/positive-collateral');
    // 2. perform debt repayment
    uint debtValue = BToken(pos.bToken).fetchDebtShareValue(pos.debtShare);
    _amount = Math.min(_amount, debtValue);
    uint debtShare = BToken(pos.bToken).repay(msg.sender, _amount);
    pos.debtShare -= debtShare;
    positions[_owner][_pid].debtShare = pos.debtShare;
    emit SelflessLiquidate(_owner, _pid, _amount, debtShare, msg.sender);
  }

  /// @dev Recovers lost tokens by the governor. This function is extremely powerful so be careful.
  /// @param _bToken The BToken to propagate this recover call.
  /// @param _token The ERC20 token to recover.
  /// @param _amount The amount of tokens to recover.
  function recover(
    address _bToken,
    address _token,
    uint _amount
  ) external onlyGov lock {
    require(underlyings[_bToken] != address(0), 'recover/not-bToken');
    BToken(_bToken).recover(_token, msg.sender, _amount);
  }

  /// @dev Returns the current LTV of the given position.
  function _fetchPositionLTV(Position memory pos) internal returns (uint) {
    if (pos.debtShare == 0) {
      return 0; // no debt means zero LTV
    }

    address oracle_ = oracle; // gas saving
    uint collFactor = IBetaConfig(config).getCollFactor(pos.collateral);
    require(collFactor > 0, 'fetch/bad-collateral');
    uint debtSize = BToken(pos.bToken).fetchDebtShareValue(pos.debtShare);
    uint debtValue = IBetaOracle(oracle_).getAssetETHValue(underlyings[pos.bToken], debtSize);
    uint collCred = (pos.collateralSize * collFactor) / 1e18;
    uint collValue = IBetaOracle(oracle_).getAssetETHValue(pos.collateral, collCred);

    if (debtValue >= collValue) {
      return 1e18; // 100% LTV is very very bad and must always be liquidatable and unsafe
    }
    return (debtValue * 1e18) / collValue;
  }
}
