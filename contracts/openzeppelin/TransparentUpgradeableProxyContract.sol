// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.3;

import 'OpenZeppelin/openzeppelin-contracts@4.0.0/contracts/proxy/transparent/TransparentUpgradeableProxy.sol';

contract TransparentUpgradeableProxyContract is TransparentUpgradeableProxy {
  constructor(
    address _logic,
    address admin_,
    bytes memory _data
  ) payable TransparentUpgradeableProxy(_logic, admin_, _data) {}
}
