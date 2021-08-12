// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.6;

import 'OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/token/ERC20/ERC20.sol';

contract MockWETH is ERC20 {
  constructor() ERC20('WETH', 'WETH') {}

  function deposit() external payable {
    _mint(msg.sender, msg.value);
  }

  function withdraw(uint amount) external {
    _burn(msg.sender, amount);
    (bool success, ) = msg.sender.call{value: amount}(new bytes(0));
    require(success, '!success');
  }
}
