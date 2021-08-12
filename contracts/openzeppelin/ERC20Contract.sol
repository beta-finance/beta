// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

import 'OpenZeppelin/openzeppelin-contracts@4.0.0/contracts/access/Ownable.sol';
import 'OpenZeppelin/openzeppelin-contracts@4.0.0/contracts/token/ERC20/ERC20.sol';

contract ERC20Contract is ERC20, Ownable {
  constructor(string memory name_, string memory symbol_) ERC20(name_, symbol_) {}

  function mint(address account, uint amount) external onlyOwner {
    _mint(account, amount);
  }

  function burn(address account, uint amount) external onlyOwner {
    _burn(account, amount);
  }
}
