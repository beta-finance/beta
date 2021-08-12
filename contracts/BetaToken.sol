// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

import 'OpenZeppelin/openzeppelin-contracts@4.0.0/contracts/token/ERC20/presets/ERC20PresetMinterPauser.sol';
import 'OpenZeppelin/openzeppelin-contracts@4.0.0/contracts/token/ERC20/extensions/draft-ERC20Permit.sol';

contract BetaToken is ERC20PresetMinterPauser('Beta Token', 'BETA'), ERC20Permit('BETA') {
  function _beforeTokenTransfer(
    address from,
    address to,
    uint amount
  ) internal virtual override(ERC20, ERC20PresetMinterPauser) {
    ERC20PresetMinterPauser._beforeTokenTransfer(from, to, amount);
  }
}
