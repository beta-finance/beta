// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

import 'OpenZeppelin/openzeppelin-contracts@4.0.0/contracts/token/ERC20/extensions/draft-ERC20Permit.sol';
import 'OpenZeppelin/openzeppelin-contracts@4.0.0/contracts/token/ERC20/utils/SafeERC20.sol';
import 'OpenZeppelin/openzeppelin-contracts@4.0.0/contracts/security/ReentrancyGuard.sol';
import 'OpenZeppelin/openzeppelin-contracts@4.0.0/contracts/security/Pausable.sol';

import '../interfaces/IBetaBank.sol';
import '../interfaces/IBetaConfig.sol';
import '../interfaces/IBetaInterestModel.sol';

interface IERC20Metadata {
  /// @dev Returns the name of the token.
  function name() external view returns (string memory);

  /// @dev Returns the symbol of the token.
  function symbol() external view returns (string memory);

  /// @dev Returns the decimals places of the token.
  function decimals() external view returns (uint8);
}

contract BToken is ERC20Permit, ReentrancyGuard {
  using SafeERC20 for IERC20;
  uint public constant MINIMUM_LIQUIDITY = 10**6;

  event Accrue(uint interest);
  event Mint(address caller, address to, uint amount, uint credit);
  event Burn(address caller, address to, uint amount, uint credit);

  address public immutable betaBank;
  address public immutable underlying;

  uint public interestRate;
  uint public lastAccrueTime;
  uint public totalAvailable;
  uint public totalLoan;
  uint public totalDebtShare;

  constructor(address _betaBank, address _underlying)
    ERC20Permit('B Token')
    ERC20('B Token', 'bTOKEN')
  {
    betaBank = _betaBank;
    underlying = _underlying;
    interestRate = IBetaInterestModel(IBetaBank(_betaBank).interestModel()).initialRate();
    lastAccrueTime = block.timestamp;
  }

  /// @dev Returns the name of the token.
  function name() public view override returns (string memory) {
    try IERC20Metadata(underlying).name() returns (string memory data) {
      return string(abi.encodePacked('B ', data));
    } catch (bytes memory) {
      return ERC20.name();
    }
  }

  /// @dev Returns the symbol of the token.
  function symbol() public view override returns (string memory) {
    try IERC20Metadata(underlying).symbol() returns (string memory data) {
      return string(abi.encodePacked('b', data));
    } catch (bytes memory) {
      return ERC20.symbol();
    }
  }

  /// @dev Returns the decimals places of the token.
  function decimals() public view override returns (uint8) {
    try IERC20Metadata(underlying).decimals() returns (uint8 data) {
      return data;
    } catch (bytes memory) {
      return ERC20.decimals();
    }
  }

  /// @dev Accrues interest rate and adjust the rate. Can be called by anyone at any time.
  function accrue() public {
    // 1. Check time past condition
    uint timePast = block.timestamp - lastAccrueTime;
    if (timePast <= 0) return;
    lastAccrueTime = block.timestamp;
    // 2. Check bank pause condition
    require(!Pausable(betaBank).paused(), 'BetaBank/paused');
    // 3. Compute the accrued interest value over the past time
    (uint totalLoan_, uint totalAvailable_, uint interestRate_) =
      (totalLoan, totalAvailable, interestRate); // gas saving by avoiding multiple SLOADs
    IBetaConfig config = IBetaConfig(IBetaBank(betaBank).config());
    IBetaInterestModel model = IBetaInterestModel(IBetaBank(betaBank).interestModel());
    uint interest = (interestRate_ * totalLoan_ * timePast) / (365 days) / 1e18;
    // 4. Update total loan and next interest rate
    totalLoan_ += interest;
    totalLoan = totalLoan_;
    interestRate = model.getNextInterestRate(interestRate_, totalAvailable_, totalLoan_, timePast);
    // 5. Send a portion of collected interest to the beneficiary
    if (interest > 0) {
      uint reserveRate = config.reserveRate();
      if (reserveRate > 0) {
        uint toReserve = (interest * reserveRate) / 1e18;
        _mint(
          config.reserveBeneficiary(),
          (toReserve * totalSupply()) / (totalLoan_ + totalAvailable_ - toReserve)
        );
      }
      emit Accrue(interest);
    }
  }

  /// @dev Returns the debt value for the given debt share. Automatically calls accrue.
  function fetchDebtShareValue(uint _debtShare) external returns (uint) {
    accrue();
    if (_debtShare == 0) {
      return 0;
    }
    return ((_debtShare * totalLoan) + totalDebtShare - 1) / totalDebtShare; // round up
  }

  /// @dev Mints new bToken to the given address.
  /// @param _to The address to mint new bToken for.
  /// @param _amount The amount of underlying tokens to deposit via `transferFrom`.
  /// @return credit The amount of bToken minted.
  function mint(address _to, uint _amount) external nonReentrant returns (uint credit) {
    accrue();
    uint amount;
    {
      uint balBefore = IERC20(underlying).balanceOf(address(this));
      IERC20(underlying).safeTransferFrom(msg.sender, address(this), _amount);
      uint balAfter = IERC20(underlying).balanceOf(address(this));
      amount = balAfter - balBefore;
    }
    uint supply = totalSupply();
    if (supply == 0) {
      credit = amount - MINIMUM_LIQUIDITY;
      // Permanently lock the first MINIMUM_LIQUIDITY tokens
      totalAvailable += credit;
      totalLoan += MINIMUM_LIQUIDITY;
      totalDebtShare += MINIMUM_LIQUIDITY;
      _mint(address(1), MINIMUM_LIQUIDITY); // OpenZeppelin ERC20 does not allow minting to 0
    } else {
      credit = (amount * supply) / (totalAvailable + totalLoan);
      totalAvailable += amount;
    }
    require(credit > 0, 'mint/no-credit-minted');
    _mint(_to, credit);
    emit Mint(msg.sender, _to, _amount, credit);
  }

  /// @dev Burns the given bToken for the proportional amount of underlying tokens.
  /// @param _to The address to send the underlying tokens to.
  /// @param _credit The amount of bToken to burn.
  /// @return amount The amount of underlying tokens getting transferred out.
  function burn(address _to, uint _credit) external nonReentrant returns (uint amount) {
    accrue();
    uint supply = totalSupply();
    amount = (_credit * (totalAvailable + totalLoan)) / supply;
    require(amount > 0, 'burn/no-amount-returned');
    totalAvailable -= amount;
    _burn(msg.sender, _credit);
    IERC20(underlying).safeTransfer(_to, amount);
    emit Burn(msg.sender, _to, amount, _credit);
  }

  /// @dev Borrows the funds for the given address. Must only be called by BetaBank.
  /// @param _to The address to borrow the funds for.
  /// @param _amount The amount to borrow.
  /// @param debtShare The amount of new debt share minted.
  function borrow(address _to, uint _amount) external nonReentrant returns (uint debtShare) {
    require(msg.sender == betaBank, 'borrow/not-BetaBank');
    accrue();
    IERC20(underlying).safeTransfer(_to, _amount);
    debtShare = ((_amount * totalDebtShare) + totalLoan - 1) / totalLoan; // round up
    totalAvailable -= _amount;
    totalLoan += _amount;
    totalDebtShare += debtShare;
  }

  /// @dev Repays the debt using funds from the given address. Must only be called by BetaBank.
  /// @param _from The address to drain the funds to repay.
  /// @param _amount The amount of funds to call via `transferFrom`.
  /// @return debtShare The amount of debt share repaid.
  function repay(address _from, uint _amount) external nonReentrant returns (uint debtShare) {
    require(msg.sender == betaBank, 'repay/not-BetaBank');
    accrue();
    uint amount;
    {
      uint balBefore = IERC20(underlying).balanceOf(address(this));
      IERC20(underlying).safeTransferFrom(_from, address(this), _amount);
      uint balAfter = IERC20(underlying).balanceOf(address(this));
      amount = balAfter - balBefore;
    }
    require(amount <= totalLoan, 'repay/amount-too-high');
    debtShare = (amount * totalDebtShare) / totalLoan; // round down
    totalAvailable += amount;
    totalLoan -= amount;
    totalDebtShare -= debtShare;
    require(totalDebtShare >= MINIMUM_LIQUIDITY, 'repay/too-low-sum-debt-share');
  }

  /// @dev Recovers tokens in this contract. EMERGENCY ONLY. Full trust in BetaBank.
  /// @param _token The token to recover, can even be underlying so please be careful.
  /// @param _to The address to recover tokens to.
  /// @param _amount The amount of tokens to recover, or MAX_UINT256 if whole balance.
  function recover(
    address _token,
    address _to,
    uint _amount
  ) external nonReentrant {
    require(msg.sender == betaBank, 'recover/not-BetaBank');
    if (_amount == type(uint).max) {
      _amount = IERC20(_token).balanceOf(address(this));
    }
    IERC20(_token).safeTransfer(_to, _amount);
  }
}
