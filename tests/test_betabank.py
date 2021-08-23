import pytest
import brownie
from brownie import (
    a,
    chain,
    BetaBank,
    BToken,
    BetaConfig,
    BetaOracleUniswapV2,
    BetaInterestModelV1,
    MockExternalOracle,
    ERC20Contract,
    MockExternalOracle,
    MockIsPermittedCallerTester,
    BTokenDeployer,
    MockSameBlockTxTester,
)


ZERO = "0x0000000000000000000000000000000000000000"
ONE = "0x0000000000000000000000000000000000000001"
# Mocking arbitrary addresses
WETH = "0x4de688DF50200AaAFada86898330Fc9aB2E6F4CC"


def mathval(val):
    return int(val * 1000000) * 10 ** 12


def test_betabank_governor():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5)
    )
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), ONE, config, im)
    assert betaBank.governor() == a[0]
    assert betaBank.pendingGovernor() == ZERO
    with brownie.reverts("BetaBank/onlyGov"):
        betaBank.setPendingGovernor(a[1], {"from": a[1]})
    with brownie.reverts("acceptGovernor/not-pending-governor"):
        betaBank.acceptGovernor({"from": a[1]})
    betaBank.setPendingGovernor(a[1], {"from": a[0]})
    assert betaBank.governor() == a[0]
    assert betaBank.pendingGovernor() == a[1]
    with brownie.reverts("acceptGovernor/not-pending-governor"):
        betaBank.acceptGovernor({"from": a[0]})
    betaBank.acceptGovernor({"from": a[1]})
    assert betaBank.governor() == a[1]
    assert betaBank.pendingGovernor() == ZERO
    with brownie.reverts("BetaBank/onlyGov"):
        betaBank.setPendingGovernor(a[2], {"from": a[0]})
    betaBank.setPendingGovernor(a[2], {"from": a[1]})
    assert betaBank.governor() == a[1]
    assert betaBank.pendingGovernor() == a[2]


def test_betabank_setters_getters():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5)
    )
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), a[1], config, im)
    assert betaBank.config() == config
    assert betaBank.interestModel() == im
    assert betaBank.oracle() == a[1]
    with brownie.reverts("BetaBank/onlyGov"):
        betaBank.setConfig(a[5], {"from": a[1]})
    with brownie.reverts("BetaBank/onlyGov"):
        betaBank.setInterestModel(a[5], {"from": a[1]})
    with brownie.reverts("BetaBank/onlyGov"):
        betaBank.setOracle(a[5], {"from": a[1]})
    betaBank.setConfig(a[2], {"from": a[0]})
    betaBank.setInterestModel(a[3], {"from": a[0]})
    betaBank.setOracle(a[4], {"from": a[0]})
    assert betaBank.config() == a[2]
    assert betaBank.interestModel() == a[3]
    assert betaBank.oracle() == a[4]


def test_betabank_whitelist_setting_runner():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5)
    )
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), ONE, config, im)
    with brownie.reverts("BetaBank/onlyGov"):
        betaBank.setRunnerWhitelists([a[5]], True, {"from": a[1]})
    assert not betaBank.runnerWhitelists(a[5])
    betaBank.setRunnerWhitelists([a[5]], True, {"from": a[0]})
    assert betaBank.runnerWhitelists(a[5])
    assert not betaBank.runnerWhitelists(a[6])
    betaBank.setRunnerWhitelists([a[5]], False, {"from": a[0]})
    assert not betaBank.runnerWhitelists(a[5])


def test_betabank_whitelist_setting_owner():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5)
    )
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), ONE, config, im)
    with brownie.reverts("BetaBank/onlyGov"):
        betaBank.setOwnerWhitelists([a[1]], True, {"from": a[1]})
    betaBank.setOwnerWhitelists([a[1]], True, {"from": a[0]})
    assert betaBank.ownerWhitelists(a[1])
    assert not betaBank.ownerWhitelists(a[6])
    betaBank.setOwnerWhitelists([a[1]], False, {"from": a[0]})
    assert not betaBank.ownerWhitelists(a[1])


def test_betabank_allow_action_self():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5)
    )
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), a[1], config, im)
    tester = a[0].deploy(MockIsPermittedCallerTester, betaBank)
    betaBank.setOwnerWhitelists([a[1]], True, {"from": a[0]})
    assert tester.checkIsPermittedCaller(a[1], a[1], {"from": a[1]}).return_value
    assert tester.checkIsPermittedCaller(a[1], a[1], {"from": a[0]}).return_value
    assert not tester.checkIsPermittedCaller(a[1], a[0], {"from": a[1]}).return_value
    assert not tester.checkIsPermittedCaller(a[1], a[0], {"from": a[0]}).return_value


def test_betabank_allow_action_global():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5)
    )
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), a[1], config, im)
    tester = a[0].deploy(MockIsPermittedCallerTester, betaBank)
    assert not tester.checkIsPermittedCaller(a[1], a[5], {"from": a[1]}).return_value
    betaBank.setRunnerWhitelists([a[5]], True, {"from": a[0]})
    assert not tester.checkIsPermittedCaller(a[1], a[5], {"from": a[0]}).return_value
    assert tester.checkIsPermittedCaller(a[1], a[5], {"from": a[1]}).return_value


def test_betabank_public_create():
    chain.reset()
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5)
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    utoken1 = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken2 = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    ext.setETHPrice(utoken1, 2 ** 112, {"from": a[0]})
    ext.setETHPrice(utoken2, 2 ** 112, {"from": a[0]})
    oracle.setExternalOracle([utoken1, utoken2], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken1, {"from": a[0]})
    with brownie.reverts("create/unauthorized"):
        betaBank.create(utoken2, {"from": a[1]})
    with brownie.reverts("BetaBank/onlyGov"):
        betaBank.setAllowPublicCreate(True, {"from": a[1]})
    betaBank.setAllowPublicCreate(True, {"from": a[0]})
    betaBank.create(utoken2, {"from": a[1]})


def test_betabank_open():
    chain.reset()
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[0], mathval(1000000))
    ext.setETHPrice(utoken, 2 ** 112, {"from": a[0]})
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.setOwnerWhitelists([a[0], a[1]], True, {"from": a[0]})
    with brownie.reverts("open/bad-underlying"):
        betaBank.open(a[0], utoken, ctoken, {"from": a[0]})
    betaBank.create(utoken)
    btoken = BToken.at(betaBank.bTokens(utoken))
    with brownie.reverts("BetaBank/isPermittedByOwner"):
        betaBank.open(a[0], utoken, ctoken, {"from": a[1]})
    with brownie.reverts("getCollFactor/no-collateral-factor"):
        betaBank.open(a[0], utoken, ctoken, {"from": a[0]})
    config.setCollInfos([ctoken], [mathval(0.5)], [2 ** 256 - 1] * 1, {"from": a[0]})
    pid = betaBank.open(a[0], utoken, ctoken, {"from": a[0]}).return_value
    assert pid == 0
    pid = betaBank.open(a[0], utoken, ctoken, {"from": a[0]}).return_value
    assert pid == 1
    assert betaBank.nextPositionIds(a[0]) == 2
    assert betaBank.nextPositionIds(a[1]) == 0
    assert betaBank.positions(a[0], 1) == (0, 0, btoken, ctoken, 0, 0)
    pid = betaBank.open(a[1], utoken, ctoken, {"from": a[1]}).return_value
    assert pid == 0
    assert betaBank.nextPositionIds(a[0]) == 2
    assert betaBank.nextPositionIds(a[1]) == 1


def test_betabank_open_prices():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[0], mathval(1000000))
    ext.setETHPrice(utoken, 2 ** 112, {"from": a[0]})
    ext.setETHPrice(ctoken, 0, {"from": a[0]})
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.setOwnerWhitelists([a[0]], True, {"from": a[0]})
    config.setCollInfos([ctoken], [mathval(0.5)], [2 ** 256 - 1] * 1, {"from": a[0]})
    with brownie.reverts("open/no-price"):
        betaBank.open(a[0], utoken, ctoken, {"from": a[0]})
    assert betaBank.nextPositionIds(a[0]) == 0


def test_betabank_basic_put_take():
    chain.reset()
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[0], mathval(1000000))
    ext.setETHPrice(utoken, 2 ** 112, {"from": a[0]})
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.setOwnerWhitelists([a[0], a[1]], True, {"from": a[0]})
    betaBank.create(utoken)
    btoken = BToken.at(betaBank.bTokens(utoken))
    config.setCollInfos([ctoken], [mathval(0.5)], [2 ** 256 - 1] * 1, {"from": a[0]})
    pid = betaBank.open(a[0], utoken, ctoken, {"from": a[0]}).return_value
    assert pid == 0
    pid = betaBank.open(a[0], utoken, ctoken, {"from": a[0]}).return_value
    assert pid == 1
    with brownie.reverts("ERC20: transfer amount exceeds allowance"):
        betaBank.put(a[0], pid, mathval(100), {"from": a[0]})
    ctoken.approve(betaBank, 2 ** 256 - 1, {"from": a[0]})
    with brownie.reverts("BetaBank/checkPID"):
        betaBank.put(a[0], 42, mathval(100), {"from": a[0]})
    with brownie.reverts("BetaBank/isPermittedByOwner"):
        betaBank.put(a[0], pid, mathval(100), {"from": a[1]})
    betaBank.put(a[0], pid, mathval(100), {"from": a[0]})
    assert betaBank.positions(a[0], 1) == (25, 0, btoken, ctoken, mathval(100), 0)
    assert betaBank.totalCollaterals(ctoken) == mathval(100)
    with brownie.reverts("BetaBank/checkPID"):
        betaBank.take(a[0], 42, mathval(25), {"from": a[0]})
    with brownie.reverts("BetaBank/isPermittedByOwner"):
        betaBank.take(a[0], pid, mathval(25), {"from": a[1]})
    with brownie.reverts("Integer overflow"):
        betaBank.take(a[0], pid, mathval(125), {"from": a[0]})
    betaBank.take(a[0], pid, mathval(25), {"from": a[0]})
    ctoken.transfer(a[3], mathval(25), {"from": a[0]})
    assert betaBank.positions(a[0], 1) == (25, 29, btoken, ctoken, mathval(75), 0)
    assert ctoken.balanceOf(a[3]) == mathval(25)
    assert ctoken.balanceOf(betaBank) == mathval(75)
    assert betaBank.totalCollaterals(ctoken) == mathval(75)


def test_betabank_put_over_cap():
    chain.reset()
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[0], mathval(1000000))
    ext.setETHPrice(utoken, 2 ** 112, {"from": a[0]})
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.setOwnerWhitelists([a[0], a[1]], True, {"from": a[0]})
    betaBank.create(utoken)
    btoken = BToken.at(betaBank.bTokens(utoken))
    config.setCollInfos([ctoken], [mathval(0.5)], [mathval(100)], {"from": a[0]})
    pid = betaBank.open(a[0], utoken, ctoken, {"from": a[0]}).return_value
    assert pid == 0
    pid = betaBank.open(a[0], utoken, ctoken, {"from": a[0]}).return_value
    assert pid == 1
    with brownie.reverts("ERC20: transfer amount exceeds allowance"):
        betaBank.put(a[0], pid, mathval(100), {"from": a[0]})
    ctoken.approve(betaBank, 2 ** 256 - 1, {"from": a[0]})
    with brownie.reverts("BetaBank/checkPID"):
        betaBank.put(a[0], 42, mathval(100), {"from": a[0]})
    with brownie.reverts("BetaBank/isPermittedByOwner"):
        betaBank.put(a[0], pid, mathval(100), {"from": a[1]})
    with brownie.reverts("put/too-much-collateral"):
        betaBank.put(a[0], pid, mathval(100) + 1, {"from": a[0]})
    betaBank.put(a[0], pid, mathval(100), {"from": a[0]})
    assert betaBank.positions(a[0], 1) == (26, 0, btoken, ctoken, mathval(100), 0)
    with brownie.reverts("BetaBank/checkPID"):
        betaBank.take(a[0], 42, mathval(25), {"from": a[0]})
    with brownie.reverts("BetaBank/isPermittedByOwner"):
        betaBank.take(a[0], pid, mathval(25), {"from": a[1]})
    with brownie.reverts("Integer overflow"):
        betaBank.take(a[0], pid, mathval(125), {"from": a[0]})
    betaBank.take(a[0], pid, mathval(25), {"from": a[0]})
    ctoken.transfer(a[3], mathval(25), {"from": a[0]})
    assert betaBank.positions(a[0], 1) == (26, 30, btoken, ctoken, mathval(75), 0)
    assert ctoken.balanceOf(a[3]) == mathval(25)
    assert ctoken.balanceOf(betaBank) == mathval(75)


def test_betabank_multiple_put():
    chain.reset()
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[0], mathval(1000000))
    ext.setETHPrice(utoken, 2 ** 112, {"from": a[0]})
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.setOwnerWhitelists([a[0]], True, {"from": a[0]})
    btoken = BToken.at(betaBank.bTokens(utoken))
    config.setCollInfos([ctoken], [mathval(0.5)], [2 ** 256 - 1] * 1, {"from": a[0]})
    pid = betaBank.open(a[0], utoken, ctoken, {"from": a[0]}).return_value
    assert pid == 0
    pid = betaBank.open(a[0], utoken, ctoken, {"from": a[0]}).return_value
    assert pid == 1
    ctoken.approve(betaBank, 2 ** 256 - 1, {"from": a[0]})
    betaBank.put(a[0], pid, mathval(50), {"from": a[0]})
    betaBank.put(a[0], pid, mathval(50), {"from": a[0]})
    assert betaBank.positions(a[0], 1) == (23, 0, btoken, ctoken, mathval(100), 0)


def test_betabank_basic_borrow_repay():
    chain.reset()
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[1], mathval(1000000))
    ext.setETHPrice(utoken, 3 * 2 ** 112, {"from": a[0]})  # utoken price is 3 ETH
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})  # ctoken price is 1 ETH
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.setOwnerWhitelists([a[1]], True, {"from": a[0]})
    btoken = BToken.at(betaBank.bTokens(utoken))
    config.setCollInfos(
        [ctoken], [mathval(0.8)], [2 ** 256 - 1] * 1, {"from": a[0]}
    )  # 80% collateral factor
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})
    pid = betaBank.open(a[1], utoken, ctoken, {"from": a[1]}).return_value
    assert pid == 0
    ctoken.approve(betaBank, 2 ** 256 - 1, {"from": a[1]})
    betaBank.put(a[1], pid, mathval(500), {"from": a[1]})
    assert betaBank.fetchPositionLTV(a[1], pid).return_value == 0
    with brownie.reverts("BetaBank/checkPID"):
        betaBank.borrow(a[1], 42, mathval(10), {"from": a[1]})
    with brownie.reverts("BetaBank/isPermittedByOwner"):
        betaBank.borrow(a[1], pid, mathval(10), {"from": a[0]})
    with brownie.reverts("borrow/not-safe"):
        betaBank.borrow(a[1], pid, mathval(50), {"from": a[1]})
    betaBank.borrow(a[1], pid, mathval(20), {"from": a[1]})
    assert betaBank.fetchPositionLTV(a[1], pid).return_value == mathval(
        0.15
    )  # (20*3) / (500*1*0.8)
    assert betaBank.positions(a[1], pid) == (
        28,
        0,
        btoken,
        ctoken,
        mathval(500),
        mathval(20),
    )
    assert utoken.balanceOf(a[1]) == mathval(20)
    assert btoken.totalLoan() == 20000000000001000000
    with brownie.reverts("ERC20: transfer amount exceeds allowance"):
        betaBank.repay(a[1], pid, mathval(5), {"from": a[1]})
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[1]})
    with brownie.reverts("BetaBank/checkPID"):
        betaBank.repay(a[1], 42, mathval(5), {"from": a[1]})
    with brownie.reverts("BetaBank/isPermittedByOwner"):
        betaBank.repay(a[1], pid, mathval(5), {"from": a[0]})
    betaBank.repay(a[1], pid, mathval(5), {"from": a[1]})
    assert betaBank.fetchPositionLTV(a[1], pid).return_value == mathval(
        0.1125
    )  # (15*3) / (500*1*0.8)
    assert betaBank.positions(a[1], pid) == (
        28,
        34,
        btoken,
        ctoken,
        mathval(500),
        mathval(15),
    )
    assert utoken.balanceOf(a[1]) == mathval(15)
    assert btoken.totalLoan() == 15000000000001000000


def test_betabank_interest_liquidate():
    chain.reset()
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.2), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[1], mathval(1000000))
    ext.setETHPrice(utoken, 3 * 2 ** 112, {"from": a[0]})  # utoken price is 3 ETH
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})  # ctoken price is 1 ETH
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.setOwnerWhitelists([a[1]], True, {"from": a[0]})
    btoken = BToken.at(betaBank.bTokens(utoken))
    config.setCollInfos(
        [ctoken], [mathval(0.8)], [2 ** 256 - 1] * 1, {"from": a[0]}
    )  # 80% collateral factor
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})
    pid = betaBank.open(a[1], utoken, ctoken, {"from": a[1]}).return_value
    assert pid == 0
    ctoken.approve(betaBank, 2 ** 256 - 1, {"from": a[1]})
    betaBank.put(a[1], pid, mathval(500), {"from": a[1]})
    assert betaBank.fetchPositionLTV(a[1], pid).return_value == 0
    assert betaBank.totalCollaterals(ctoken) == mathval(500)
    betaBank.borrow(a[1], pid, mathval(40), {"from": a[1]})
    assert float(betaBank.fetchPositionLTV(a[1], pid).return_value) == pytest.approx(
        mathval(0.30)
    )  # (40*3) / (500*1*0.8)
    assert betaBank.positions(a[1], pid) == (
        25,
        0,
        btoken,
        ctoken,
        mathval(500),
        mathval(40),
    )
    chain.sleep(365 * 86400)
    assert float(betaBank.fetchPositionLTV(a[1], pid).return_value) == pytest.approx(
        mathval(0.36)
    )  # 20% interest
    chain.sleep(365 * 86400)
    assert float(betaBank.fetchPositionLTV(a[1], pid).return_value) == pytest.approx(
        mathval(0.432)
    )  # 20% interest
    with brownie.reverts("liquidate/not-liquidatable"):
        betaBank.liquidate(a[1], pid, mathval(10), {"from": a[0]})
    chain.sleep(365 * 86400)
    assert float(betaBank.fetchPositionLTV(a[1], pid).return_value) == pytest.approx(
        mathval(0.5184)
    )  # 20% interest
    assert betaBank.positions(a[1], pid) == (
        25,
        0,
        btoken,
        ctoken,
        mathval(500),
        mathval(40),
    )
    assert float(btoken.totalLoan()) == pytest.approx(mathval(69.12))
    assert float(btoken.totalDebtShare()) == pytest.approx(mathval(40))
    with brownie.reverts("BetaBank/checkPID"):
        betaBank.liquidate(a[1], 42, mathval(30), {"from": a[0]})
    with brownie.reverts("liquidate/too-much-liquidation"):
        betaBank.liquidate(a[1], pid, mathval(69.12 / 2 + 0.01), {"from": a[0]})
    betaBank.liquidate.call(
        a[1], pid, mathval(69.12 / 2), {"from": a[0]}
    )  # try call should not revert
    with brownie.reverts("liquidate/too-much-liquidation"):
        betaBank.liquidate(a[1], pid, mathval(40), {"from": a[0]})
    assert ctoken.balanceOf(a[0]) == 0
    betaBank.liquidate(a[1], pid, mathval(30), {"from": a[0]})
    assert float(btoken.totalLoan()) == pytest.approx(mathval(39.12))
    assert float(btoken.totalDebtShare()) == pytest.approx(mathval(22.638889))
    assert float(ctoken.balanceOf(a[0])) == pytest.approx(mathval(94.5))  # 30*3*1.05
    assert float(betaBank.fetchPositionLTV(a[1], pid).return_value) == pytest.approx(
        mathval(0.361775), rel=1e-3
    )
    [_, _, _, _, coll, debt] = betaBank.positions(a[1], pid)
    assert float(coll) == pytest.approx(mathval(405.5))
    assert float(debt) == pytest.approx(mathval(22.638889))
    assert float(betaBank.totalCollaterals(ctoken)) == pytest.approx(
        mathval(500) - mathval(94.5), rel=1e-3
    )


def test_betabank_pausable():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.2), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[1], mathval(1000000))
    ext.setETHPrice(utoken, 3 * 2 ** 112, {"from": a[0]})  # utoken price is 3 ETH
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})  # ctoken price is 1 ETH
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    btoken = BToken.at(betaBank.bTokens(utoken))
    config.setCollInfos(
        [ctoken], [mathval(0.8)], [2 ** 256 - 1] * 1, {"from": a[0]}
    )  # 80% collateral factor
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})
    with brownie.reverts("BetaBank/onlyGov"):
        betaBank.pause({"from": a[1]})
    betaBank.pause({"from": a[0]})
    with brownie.reverts("Pausable: paused"):
        betaBank.pause({"from": a[0]})
    assert betaBank.paused()
    with brownie.reverts("Pausable: paused"):
        betaBank.open(a[1], utoken, ctoken, {"from": a[1]})
    with brownie.reverts("BetaBank/onlyGov"):
        betaBank.unpause({"from": a[2]})
    betaBank.unpause({"from": a[0]})
    with brownie.reverts("Pausable: not paused"):
        betaBank.unpause({"from": a[0]})
    assert not betaBank.paused()
    betaBank.setOwnerWhitelists([a[1]], True, {"from": a[0]})
    pid = betaBank.open(a[1], utoken, ctoken, {"from": a[1]}).return_value
    assert pid == 0
    ctoken.approve(betaBank, 2 ** 256 - 1, {"from": a[1]})
    betaBank.pause({"from": a[0]})
    with brownie.reverts("Pausable: paused"):
        betaBank.put(a[1], pid, mathval(500), {"from": a[1]})
    with brownie.reverts("Pausable: paused"):
        betaBank.borrow(a[1], pid, mathval(20), {"from": a[1]})
    with brownie.reverts("Pausable: paused"):
        betaBank.repay(a[1], pid, mathval(5), {"from": a[1]})
    with brownie.reverts("Pausable: paused"):
        betaBank.take(a[1], pid, mathval(25), {"from": a[1]})
    with brownie.reverts("Pausable: paused"):
        betaBank.liquidate(a[1], pid, mathval(30), {"from": a[0]})
    betaBank.unpause({"from": a[0]})
    betaBank.put(a[1], pid, mathval(500), {"from": a[1]})
    betaBank.borrow(a[1], pid, mathval(40), {"from": a[1]})
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[1]})
    betaBank.repay(a[1], pid, mathval(10), {"from": a[1]})
    betaBank.take(a[1], pid, mathval(100), {"from": a[1]})
    chain.sleep(4 * 365 * 86400)
    assert float(betaBank.fetchPositionLTV(a[1], pid).return_value) == pytest.approx(
        mathval(0.50625)
    )
    betaBank.liquidate(a[1], pid, mathval(27), {"from": a[0]})


def test_betabank_borrowput_repaytake_same_block():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.2), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[1], mathval(1000000))
    ext.setETHPrice(utoken, 3 * 2 ** 112, {"from": a[0]})  # utoken price is 3 ETH
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})  # ctoken price is 1 ETH
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    btoken = BToken.at(betaBank.bTokens(utoken))
    tester = a[0].deploy(MockSameBlockTxTester, betaBank, utoken, ctoken)
    config.setCollInfos(
        [ctoken], [mathval(0.8)], [2 ** 256 - 1] * 1, {"from": a[0]}
    )  # 80% collateral factor
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})
    betaBank.setOwnerWhitelists([tester], True, {"from": a[0]})
    ctoken.transfer(tester, mathval(1000), {"from": a[1]})
    tester.init(mathval(500), mathval(20), {"from": a[1]})
    with brownie.reverts("take/bad-block"):
        tester.borrowTake(mathval(20), {"from": a[1]})
    with brownie.reverts("take/bad-block"):
        tester.putTake(mathval(100), {"from": a[1]})
    with brownie.reverts("repay/bad-block"):
        tester.borrowRepay(mathval(10), {"from": a[1]})
    with brownie.reverts("repay/bad-block"):
        tester.putRepay(mathval(10), {"from": a[1]})
    with brownie.reverts("borrow/bad-block"):
        tester.takeBorrow(mathval(20), {"from": a[1]})
    with brownie.reverts("borrow/bad-block"):
        tester.repayBorrow(mathval(10), {"from": a[1]})
    with brownie.reverts("put/bad-block"):
        tester.takePut(mathval(100), {"from": a[1]})
    with brownie.reverts("put/bad-block"):
        tester.repayPut(mathval(10), {"from": a[1]})


def test_betabank_altruistic_liquidate():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.2), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[1], mathval(1000000))
    ext.setETHPrice(utoken, 3 * 2 ** 112, {"from": a[0]})  # utoken price is 3 ETH
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})  # ctoken price is 1 ETH
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.setOwnerWhitelists([a[1]], True, {"from": a[0]})
    btoken = BToken.at(betaBank.bTokens(utoken))
    config.setCollInfos(
        [ctoken], [mathval(0.8)], [2 ** 256 - 1] * 1, {"from": a[0]}
    )  # 80% collateral factor
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})
    pid = betaBank.open(a[1], utoken, ctoken, {"from": a[1]}).return_value
    ctoken.approve(betaBank, 2 ** 256 - 1, {"from": a[1]})
    betaBank.put(a[1], pid, mathval(500), {"from": a[1]})
    betaBank.borrow(a[1], pid, mathval(40), {"from": a[1]})
    with brownie.reverts("liquidate/not-liquidatable"):
        betaBank.liquidate(a[1], pid, mathval(10), {"from": a[0]})
    with brownie.reverts("selflessLiquidate/positive-collateral"):
        betaBank.selflessLiquidate(a[1], pid, mathval(40), {"from": a[0]})
    ext.setETHPrice(ctoken, 1e-15 * 2 ** 112, {"from": a[0]})
    betaBank.liquidate(a[1], pid, mathval(1e-6), {"from": a[0]})
    assert float(btoken.totalLoan()) == pytest.approx(mathval(40))
    assert float(btoken.totalDebtShare()) == pytest.approx(mathval(40))
    assert float(ctoken.balanceOf(a[0])) == mathval(500)
    assert float(betaBank.fetchPositionLTV(a[1], pid).return_value) == mathval(1)
    [_, _, _, _, coll, debt] = betaBank.positions(a[1], pid)
    assert float(coll) == 0
    assert float(debt) == pytest.approx(mathval(40))
    betaBank.selflessLiquidate(a[1], pid, mathval(50), {"from": a[0]})
    [_, _, _, _, coll, debt] = betaBank.positions(a[1], pid)
    assert float(coll) == 0
    assert float(debt) == 0


def test_betabank_recover_underlying():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.2), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    utoken.mint(a[1], mathval(100000))

    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[1], mathval(1000000))
    ext.setETHPrice(utoken, 3 * 2 ** 112, {"from": a[0]})  # utoken price is 3 ETH
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})  # ctoken price is 1 ETH
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.setOwnerWhitelists([a[1]], True, {"from": a[0]})
    btoken = BToken.at(betaBank.bTokens(utoken))
    config.setCollInfos(
        [ctoken], [mathval(0.8)], [2 ** 256 - 1], {"from": a[0]}
    )  # 80% collateral factor
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})

    with brownie.reverts("recover/not-bToken"):
        betaBank.recover(ctoken, utoken, 1, {"from": a[0]})
    with brownie.reverts("BetaBank/onlyGov"):
        betaBank.recover(btoken, utoken, 1, {"from": a[1]})
    with brownie.reverts("recover/not-BetaBank"):
        btoken.recover(utoken, a[0], 0, {"from": a[0]})

    utoken_pre_bal = utoken.balanceOf(a[0])
    btoken_utoken_pre_bal = utoken.balanceOf(btoken)
    betaBank.recover(btoken, utoken, mathval(10), {"from": a[0]})
    utoken_pos_bal = utoken.balanceOf(a[0])
    btoken_utoken_pos_bal = utoken.balanceOf(btoken)
    assert utoken_pos_bal - utoken_pre_bal == mathval(10)
    assert btoken_utoken_pos_bal - btoken_utoken_pre_bal == -mathval(10)


def test_betabank_recover_non_underlying():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.2), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    utoken.mint(a[1], mathval(100000))

    mockToken = a[0].deploy(ERC20Contract, "Non Underlying Token Name", "NON")
    mockToken.mint(a[0], mathval(1000000))
    mockToken.mint(a[1], mathval(100000))

    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[1], mathval(1000000))
    ext.setETHPrice(utoken, 3 * 2 ** 112, {"from": a[0]})  # utoken price is 3 ETH
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})  # ctoken price is 1 ETH
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.setOwnerWhitelists([a[1]], True, {"from": a[0]})
    btoken = BToken.at(betaBank.bTokens(utoken))

    mockToken.transfer(btoken, mathval(1000), {"from": a[1]})

    with brownie.reverts("recover/not-bToken"):
        betaBank.recover(ctoken, mockToken, 1, {"from": a[0]})
    with brownie.reverts("BetaBank/onlyGov"):
        betaBank.recover(btoken, mockToken, 1, {"from": a[1]})
    with brownie.reverts("recover/not-BetaBank"):
        btoken.recover(mockToken, a[0], 0, {"from": a[0]})

    mockToken_pre_bal = mockToken.balanceOf(a[0])
    btoken_mockToken_pre_bal = mockToken.balanceOf(btoken)
    betaBank.recover(btoken, mockToken, mathval(10), {"from": a[0]})
    mockToken_pos_bal = mockToken.balanceOf(a[0])
    btoken_mockToken_pos_bal = mockToken.balanceOf(btoken)
    assert mockToken_pos_bal - mockToken_pre_bal == mathval(10)
    assert btoken_mockToken_pos_bal - btoken_mockToken_pre_bal == -mathval(10)
