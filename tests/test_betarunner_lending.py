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
    BetaRunnerLending,
    MockExternalOracle,
    ERC20Contract,
    MockExternalOracle,
    MockWETH,
    BTokenDeployer,
)


ZERO = "0x0000000000000000000000000000000000000000"
ONE = "0x0000000000000000000000000000000000000001"


def mathval(val):
    return int(val * 1000000) * 10 ** 12


@pytest.fixture
def weth():
    chain.reset()
    return a[0].deploy(MockWETH)


def test_rtlending_borrow_already_open(weth):
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, weth, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[1], mathval(1000000))
    ext.setETHPrice(utoken, 3 * 2 ** 112, {"from": a[0]})
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.create(weth)
    btoken = BToken.at(betaBank.bTokens(utoken))
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})
    config.setCollInfos([ctoken], [mathval(0.5)], [2 ** 256 - 1] * 1, {"from": a[0]})
    betaBank.setOwnerWhitelists([a[1]], True, {"from": a[0]})
    pid = betaBank.open(a[1], utoken, ctoken, {"from": a[1]}).return_value
    assert pid == 0
    rt = a[0].deploy(BetaRunnerLending, betaBank, weth)
    ctoken.approve(rt, 2 ** 256 - 1, {"from": a[1]})
    with brownie.reverts("BetaBank/isPermittedByOwner"):
        rt.borrow(pid, utoken, ctoken, mathval(20), mathval(500), {"from": a[1]})
    betaBank.setRunnerWhitelists([rt], True, {"from": a[0]})
    rt.borrow(pid, utoken, ctoken, mathval(20), mathval(500), {"from": a[1]})
    assert betaBank.positions(a[1], pid) == (
        28,
        0,
        btoken,
        ctoken,
        mathval(500),
        mathval(20),
    )


def test_rtlending_borrow_new(weth):
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, weth, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[1], mathval(1000000))
    ext.setETHPrice(utoken, 3 * 2 ** 112, {"from": a[0]})
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.create(weth)
    btoken = BToken.at(betaBank.bTokens(utoken))
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})
    config.setCollInfos([ctoken], [mathval(0.5)], [2 ** 256 - 1] * 1, {"from": a[0]})
    rt = a[0].deploy(BetaRunnerLending, betaBank, weth)
    ctoken.approve(rt, 2 ** 256 - 1, {"from": a[1]})
    betaBank.setRunnerWhitelists([rt], True, {"from": a[0]})
    rt.borrow(2 ** 256 - 1, utoken, ctoken, mathval(20), mathval(500), {"from": a[1]})
    assert betaBank.positions(a[1], 0) == (
        25,
        0,
        btoken,
        ctoken,
        mathval(500),
        mathval(20),
    )


def test_rtlending_borrow_eth_collateral(weth):
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, weth, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ext.setETHPrice(utoken, 3 * 2 ** 112, {"from": a[0]})
    oracle.setExternalOracle([utoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.create(weth)
    btoken = BToken.at(betaBank.bTokens(utoken))
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})
    config.setCollInfos([weth], [mathval(0.5)], [2 ** 256 - 1] * 1, {"from": a[0]})
    rt = a[0].deploy(BetaRunnerLending, betaBank, weth)
    betaBank.setRunnerWhitelists([rt], True, {"from": a[0]})
    rt.borrow(
        2 ** 256 - 1,
        utoken,
        weth,
        mathval(0.2),
        mathval(5),
        {"value": mathval(5), "from": a[1]},
    )
    assert betaBank.positions(a[1], 0) == (
        21,
        0,
        btoken,
        weth,
        mathval(5),
        mathval(0.2),
    )


def test_rtlending_borrow_eth_out(weth):
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, weth, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[1], mathval(1000000))
    ext.setETHPrice(ctoken, 2 ** 112 // 4, {"from": a[0]})
    oracle.setExternalOracle([ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(weth)
    btoken = BToken.at(betaBank.bTokens(weth))
    weth.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    weth.deposit({"value": mathval(10), "from": a[0]})
    btoken.mint(a[0], mathval(10), {"from": a[0]})
    config.setCollInfos([ctoken], [mathval(0.5)], [2 ** 256 - 1] * 1, {"from": a[0]})
    rt = a[0].deploy(BetaRunnerLending, betaBank, weth)
    ctoken.approve(rt, 2 ** 256 - 1, {"from": a[1]})
    betaBank.setRunnerWhitelists([rt], True, {"from": a[0]})
    bal0 = a[1].balance()
    rt.borrow(2 ** 256 - 1, weth, ctoken, mathval(1), mathval(500), {"from": a[1]})
    bal1 = a[1].balance()
    assert bal1 - bal0 == mathval(1)
    assert betaBank.positions(a[1], 0) == (
        22,
        0,
        btoken,
        ctoken,
        mathval(500),
        mathval(1),
    )


def test_rtlending_repay_basic(weth):
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, weth, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[1], mathval(1000000))
    ext.setETHPrice(utoken, 3 * 2 ** 112, {"from": a[0]})
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.create(weth)
    btoken = BToken.at(betaBank.bTokens(utoken))
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})
    config.setCollInfos([ctoken], [mathval(0.5)], [2 ** 256 - 1] * 1, {"from": a[0]})
    rt = a[0].deploy(BetaRunnerLending, betaBank, weth)
    ctoken.approve(rt, 2 ** 256 - 1, {"from": a[1]})
    betaBank.setRunnerWhitelists([rt], True, {"from": a[0]})
    rt.borrow(2 ** 256 - 1, utoken, ctoken, mathval(20), mathval(500), {"from": a[1]})
    utoken.approve(rt, 2 ** 256 - 1, {"from": a[1]})
    with brownie.reverts("Integer overflow"):
        rt.repay(0, utoken, ctoken, mathval(10), mathval(1000), {"from": a[1]})
    with brownie.reverts("take/not-safe"):
        rt.repay(0, utoken, ctoken, mathval(10), mathval(400), {"from": a[1]})
    rt.repay(0, utoken, ctoken, mathval(10), mathval(100), {"from": a[1]})
    assert betaBank.positions(a[1], 0) == (
        25,
        29,
        btoken,
        ctoken,
        mathval(400),
        mathval(10),
    )
    rt.repay(0, utoken, ctoken, mathval(1000), mathval(400), {"from": a[1]})
    assert betaBank.positions(a[1], 0) == (25, 30, btoken, ctoken, 0, 0)


def test_rtlending_repay_eth_collateral(weth):
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, weth, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    ext.setETHPrice(utoken, 3 * 2 ** 112, {"from": a[0]})
    oracle.setExternalOracle([utoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.create(weth)
    btoken = BToken.at(betaBank.bTokens(utoken))
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})
    config.setCollInfos([weth], [mathval(0.5)], [2 ** 256 - 1] * 1, {"from": a[0]})
    rt = a[0].deploy(BetaRunnerLending, betaBank, weth)
    betaBank.setRunnerWhitelists([rt], True, {"from": a[0]})
    rt.borrow(
        2 ** 256 - 1,
        utoken,
        weth,
        mathval(0.2),
        mathval(5),
        {"value": mathval(5), "from": a[1]},
    )
    assert betaBank.positions(a[1], 0) == (
        21,
        0,
        btoken,
        weth,
        mathval(5),
        mathval(0.2),
    )
    utoken.approve(rt, 2 ** 256 - 1, {"from": a[1]})
    bal0 = a[1].balance()
    rt.repay(0, utoken, weth, mathval(0.1), mathval(2), {"from": a[1]})
    bal1 = a[1].balance()
    assert bal1 - bal0 == mathval(2)


def test_rtlending_borrow_eth_underlying(weth):
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, weth, ONE, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[1], mathval(1000000))
    ext.setETHPrice(ctoken, 2 ** 112 // 4, {"from": a[0]})
    oracle.setExternalOracle([ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(weth)
    btoken = BToken.at(betaBank.bTokens(weth))
    weth.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    weth.deposit({"value": mathval(10), "from": a[0]})
    btoken.mint(a[0], mathval(10), {"from": a[0]})
    config.setCollInfos([ctoken], [mathval(0.5)], [2 ** 256 - 1] * 1, {"from": a[0]})
    rt = a[0].deploy(BetaRunnerLending, betaBank, weth)
    betaBank.setRunnerWhitelists([rt], True, {"from": a[0]})
    ctoken.approve(rt, 2 ** 256 - 1, {"from": a[1]})
    rt.borrow(2 ** 256 - 1, weth, ctoken, mathval(1), mathval(500), {"from": a[1]})
    assert betaBank.positions(a[1], 0) == (
        22,
        0,
        btoken,
        ctoken,
        mathval(500),
        mathval(1),
    )
    with brownie.reverts(""):
        rt.repay(
            0,
            weth,
            ctoken,
            mathval(0.5),
            mathval(200),
            {"value": mathval(0.2), "from": a[1]},
        )
    bal0 = a[1].balance()
    rt.repay(
        0,
        weth,
        ctoken,
        mathval(0.5),
        mathval(200),
        {"value": mathval(0.7), "from": a[1]},
    )
    bal1 = a[1].balance()
    assert bal0 - bal1 == mathval(0.5)
