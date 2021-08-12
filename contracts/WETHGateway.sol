// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

import './BToken.sol';

import '../interfaces/IWETH.sol';

contract WETHGateway {
  address public immutable bweth;
  address public immutable weth;

  constructor(address _bweth) {
    address _weth = BToken(_bweth).underlying();
    require(IWETH(_weth).approve(_bweth, type(uint).max));
    bweth = _bweth;
    weth = _weth;
  }

  /// @dev Wraps the given ETH to WETH and calls mint action on BWETH for the caller.
  /// @param _to The address to receive BToken.
  function mint(address _to) external payable returns (uint credit) {
    IWETH(weth).deposit{value: msg.value}();
    credit = BToken(bweth).mint(_to, msg.value);
  }

  /// @dev Performs burn action on BWETH and unwraps WETH back to ETH for the caller.
  /// @param _to The address to send ETH to.
  /// @param _credit The amount of BToken to burn.
  function burn(address _to, uint _credit) public returns (uint amount) {
    BToken(bweth).transferFrom(msg.sender, address(this), _credit);
    amount = BToken(bweth).burn(address(this), _credit);
    IWETH(weth).withdraw(amount);
    (bool success, ) = _to.call{value: amount}(new bytes(0));
    require(success, 'burn/eth-transfer-failed');
  }

  /// @dev Similar to burn function, but with an additional call to BToken's EIP712 permit.
  function burnWithPermit(
    address _to,
    uint _credit,
    uint _approve,
    uint _deadline,
    uint8 _v,
    bytes32 _r,
    bytes32 _s
  ) external returns (uint amount) {
    BToken(bweth).permit(msg.sender, address(this), _approve, _deadline, _v, _r, _s);
    amount = burn(_to, _credit);
  }

  receive() external payable {
    require(msg.sender == weth, '!weth');
  }
}
