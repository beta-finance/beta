import pytest
import brownie
from brownie import (
    a, chain, BetaBank, BToken, BetaConfig, BetaOracleUniswapV2, BetaInterestModelV1, MockExternalOracle,
    ERC20Contract, BTokenDeployer,
)


ZERO = '0x0000000000000000000000000000000000000000'
ONE = '0x0000000000000000000000000000000000000001'
# Mocking arbitrary addresses
WETH = '0x4de688DF50200AaAFada86898330Fc9aB2E6F4CC'


def mathval(val):
    return int(val * 1000000) * 10**12


def test_btoken_deployer():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5))
    token = a[0].deploy(ERC20Contract, 'My Token Name', 'MYSYM')
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ZERO, 3600)
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    ext.setETHPrice(token, 2**112, {'from': a[0]})
    oracle.setExternalOracle([token], ext, {'from': a[0]})
    betaBank.create(token)
    btoken = BToken.at(betaBank.bTokens(token))
    assert btoken == BTokenDeployer.at(betaBank.deployer()).bTokenFor(betaBank, token)


def test_btoken_details():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5))
    token = a[0].deploy(ERC20Contract, 'My Token Name', 'MYSYM')
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ZERO, 3600)
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    ext.setETHPrice(token, 2**112, {'from': a[0]})
    oracle.setExternalOracle([token], ext, {'from': a[0]})
    betaBank.create(token)
    btoken = BToken.at(betaBank.bTokens(token))
    assert btoken.name() == 'B My Token Name'
    assert btoken.symbol() == 'bMYSYM'
    assert btoken.decimals() == 18
    ext.setETHPrice(config, 2**112, {'from': a[0]})
    oracle.setExternalOracle([config], ext, {'from': a[0]})
    betaBank.create(config)
    btoken = BToken.at(betaBank.bTokens(config))
    assert btoken.name() == 'B Token'
    assert btoken.symbol() == 'bTOKEN'
    assert btoken.decimals() == 18


def test_btoken_basic_mint_burn():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0))
    token = a[0].deploy(ERC20Contract, 'My Token Name', 'MYSYM')
    token.mint(a[0], mathval(1000000))
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ZERO, 3600)
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    ext.setETHPrice(token, 2**112, {'from': a[0]})
    oracle.setExternalOracle([token], ext, {'from': a[0]})
    betaBank.create(token)
    btoken = BToken.at(betaBank.bTokens(token))
    with brownie.reverts('ERC20: transfer amount exceeds allowance'):
        btoken.mint(a[0], mathval(500), {'from': a[0]})
    token.approve(btoken, 2**256-1, {'from': a[0]})
    btoken.mint(a[0], mathval(500), {'from': a[0]})
    btoken.mint(a[1], mathval(500), {'from': a[0]})
    assert token.balanceOf(btoken) == mathval(1000)
    assert btoken.totalSupply() == mathval(1000)
    assert btoken.balanceOf(ONE) == 1000000
    assert btoken.balanceOf(a[0]) == 499999999999999000000
    assert btoken.balanceOf(a[1]) == mathval(500)
    assert btoken.totalAvailable() == 999999999999999000000
    assert btoken.totalLoan() == 1000000
    assert btoken.totalDebtShare() == 1000000
    with brownie.reverts('Integer overflow'):
        btoken.burn(a[2], mathval(1500), {'from': a[1]})
    btoken.burn(a[2], mathval(300), {'from': a[1]})
    assert btoken.balanceOf(a[1]) == mathval(200)
    assert token.balanceOf(a[2]) == mathval(300)


def test_btoken_borrow_repay():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(BetaInterestModelV1, mathval(0.20), mathval(0), mathval(100), mathval(0))  # 20% per year
    token = a[0].deploy(ERC20Contract, 'My Token Name', 'MYSYM')
    token.mint(a[0], mathval(1000000))
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ZERO, 3600)
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    ext.setETHPrice(token, 2**112, {'from': a[0]})
    oracle.setExternalOracle([token], ext, {'from': a[0]})
    betaBank.create(token)
    btoken = BToken.at(betaBank.bTokens(token))
    token.approve(btoken, 2**256-1, {'from': a[0]})
    btoken.mint(a[0], mathval(500), {'from': a[0]})
    btoken.mint(a[1], mathval(500), {'from': a[0]})
    with brownie.reverts('borrow/not-BetaBank'):
        btoken.borrow(a[2], mathval(100), {'from': a[0]})
    with brownie.reverts('ERC20: transfer amount exceeds balance'):
        btoken.borrow(a[2], mathval(10000), {'from': betaBank})
    btoken.borrow(a[2], mathval(100), {'from': betaBank})
    assert btoken.totalAvailable() == 899999999999999000000
    assert btoken.totalLoan() == 100000000000001000000
    assert btoken.totalDebtShare() == 100000000000001000000
    assert token.balanceOf(a[2]) == mathval(100)
    chain.sleep(365 * 86400 // 2)
    btoken.accrue({'from': a[0]})
    assert float(btoken.totalAvailable()) == pytest.approx(899999999999999000000)
    assert float(btoken.totalLoan()) == pytest.approx(110000000000001100000)
    assert float(btoken.totalDebtShare()) == pytest.approx(100000000000001000000)
    assert float(btoken.fetchDebtShareValue(100, {'from': a[0]}).return_value) == pytest.approx(110, abs=1)
    btoken.burn(a[3], mathval(200), {'from': a[1]})
    assert float(btoken.totalAvailable()) == pytest.approx(697999999999998980000)
    assert float(btoken.balanceOf(a[1])) == pytest.approx(mathval(300))
    assert float(token.balanceOf(a[3])) == pytest.approx(202000000000000020000)
    with brownie.reverts('repay/not-BetaBank'):
        btoken.repay(a[0], mathval(50), {'from': a[0]})
    with brownie.reverts('repay/amount-too-high'):
        btoken.repay(a[0], mathval(150), {'from': betaBank})
    assert (
        float(btoken.repay(a[0], mathval(50), {'from': betaBank}).return_value) ==
        pytest.approx(45454545454545454545)
    )
    assert float(btoken.totalAvailable()) == pytest.approx(747999999999998980000)
    assert float(btoken.totalLoan()) == pytest.approx(60000000000001100000)
    assert float(btoken.totalDebtShare()) == pytest.approx(54545454545455545455)


def test_btoken_interest_rebase():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(BetaInterestModelV1, mathval(0.20), mathval(0), mathval(100), mathval(0.5))  # 20% per year
    token = a[0].deploy(ERC20Contract, 'My Token Name', 'MYSYM')
    token.mint(a[0], mathval(1000000))
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ZERO, 3600)
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    ext.setETHPrice(token, 2**112, {'from': a[0]})
    oracle.setExternalOracle([token], ext, {'from': a[0]})
    betaBank.create(token)
    btoken = BToken.at(betaBank.bTokens(token))
    token.approve(btoken, 2**256-1, {'from': a[0]})
    assert btoken.interestRate() == mathval(0.20)
    chain.sleep(365 * 86400)
    btoken.accrue({'from': a[0]})
    assert btoken.interestRate() == mathval(0.20)
    btoken.mint(a[0], mathval(500), {'from': a[0]})
    chain.sleep(365 * 86400)  # almost 0% utlization rate
    btoken.accrue({'from': a[0]})
    assert btoken.interestRate() == mathval(0.10)
    btoken.borrow(a[2], mathval(300), {'from': betaBank})
    chain.sleep(2 * 86400)  # ~60% utlization rate
    btoken.accrue({'from': a[0]})
    assert float(btoken.interestRate()) == pytest.approx(mathval(0.075), rel=1e-3)
    btoken.borrow(a[2], mathval(199), {'from': betaBank})
    chain.sleep(86400 // 2)  # ~100% utlization rate
    btoken.accrue({'from': a[0]})
    assert float(btoken.interestRate()) == pytest.approx(mathval(0.1125), rel=1e-2)


def test_btoken_accrue_interest():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(BetaInterestModelV1, mathval(0.10), mathval(0), mathval(100), mathval(0.5))  # 10% per year
    token = a[0].deploy(ERC20Contract, 'My Token Name', 'MYSYM')
    token.mint(a[0], mathval(1000000))
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ZERO, 3600)
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    ext.setETHPrice(token, 2**112, {'from': a[0]})
    oracle.setExternalOracle([token], ext, {'from': a[0]})
    betaBank.create(token)
    btoken = BToken.at(betaBank.bTokens(token))
    token.approve(btoken, 2**256-1, {'from': a[0]})
    chain.sleep(86400)
    btoken.accrue({'from': a[0]})
    assert btoken.interestRate() == mathval(0.10)
    btoken.mint(a[0], mathval(500), {'from': a[0]})
    btoken.borrow(a[2], mathval(320), {'from': betaBank})
    chain.sleep(365 * 86400)
    btoken.accrue({'from': a[0]})
    assert float(btoken.interestRate()) == pytest.approx(mathval(0.090413), rel=1e-4)


def test_btoken_beneficiary():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(BetaInterestModelV1, mathval(0.20), mathval(0), mathval(100), mathval(0))  # 20% per year
    token = a[0].deploy(ERC20Contract, 'My Token Name', 'MYSYM')
    token.mint(a[0], mathval(1000000))
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ZERO, 3600)
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    ext.setETHPrice(token, 2**112, {'from': a[0]})
    oracle.setExternalOracle([token], ext, {'from': a[0]})
    betaBank.create(token)
    btoken = BToken.at(betaBank.bTokens(token))
    token.approve(btoken, 2**256-1, {'from': a[0]})
    btoken.mint(a[0], mathval(500), {'from': a[0]})
    btoken.borrow(a[1], mathval(300), {'from': betaBank})
    chain.sleep(365 * 86400)
    btoken.accrue({'from': a[0]})
    assert float(btoken.totalLoan()) == pytest.approx(mathval(360))
    assert float(btoken.totalSupply()) == pytest.approx(mathval(500))
    config.setReserveInfo(a[2], mathval(0.2), {'from': a[0]})
    chain.sleep(365 * 86400)
    btoken.accrue({'from': a[0]})
    assert float(btoken.totalLoan()) == pytest.approx(mathval(432))
    assert float(btoken.totalSupply()) == pytest.approx(mathval(511.6580), rel=1e-3)
    assert float(btoken.balanceOf(a[2])) == pytest.approx(mathval(11.6580), rel=1e-3)
    btoken.burn(a[2], btoken.balanceOf(a[2]), {'from': a[2]})
    assert float(token.balanceOf(a[2])) == pytest.approx(mathval(14.4))


def test_btoken_paused():
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0))
    token = a[0].deploy(ERC20Contract, 'My Token Name', 'MYSYM')
    token.mint(a[0], mathval(1000000))
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ZERO, 3600)
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    ext.setETHPrice(token, 2**112, {'from': a[0]})
    oracle.setExternalOracle([token], ext, {'from': a[0]})
    betaBank.create(token)
    btoken = BToken.at(betaBank.bTokens(token))
    token.approve(btoken, 2**256-1, {'from': a[0]})
    chain.sleep(86400)
    btoken.accrue({'from': a[0]})
    betaBank.pause()
    chain.sleep(86400)
    with brownie.reverts('BetaBank/paused'):
        btoken.mint(a[0], mathval(500), {'from': a[0]})
    with brownie.reverts('BetaBank/paused'):
        btoken.borrow(a[1], mathval(300), {'from': betaBank})
    with brownie.reverts('BetaBank/paused'):
        btoken.accrue({'from': a[0]})
    with brownie.reverts('BetaBank/paused'):
        btoken.burn(a[2], mathval(100), {'from': a[0]})
    betaBank.unpause()
    btoken.mint(a[0], mathval(500), {'from': a[0]})
    btoken.borrow(a[1], mathval(300), {'from': betaBank})
    chain.sleep(365 * 86400)
    btoken.accrue({'from': a[0]})
    btoken.burn(a[2], mathval(100), {'from': a[0]})
