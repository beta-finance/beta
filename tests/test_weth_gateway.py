import pytest
import brownie
from brownie import (
    a, BetaBank, BToken, BetaConfig, BetaOracleUniswapV2, BetaInterestModelV1, WETHGateway, MockWETH,
    BTokenDeployer,
)


ZERO = '0x0000000000000000000000000000000000000000'
SEVEN = '0x0000000000000000000000000000000000000007'


def mathval(val):
    return int(val * 1000000) * 10**12


@pytest.fixture
def weth():
    return a[0].deploy(MockWETH)


def test_weth_gateway_mint(weth):
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0))
    oracle = a[0].deploy(BetaOracleUniswapV2, weth, ZERO, 3600)
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(weth)
    btoken = BToken.at(betaBank.bTokens(weth))
    gateway = a[0].deploy(WETHGateway, btoken)
    gateway.mint(a[1], {'value': mathval(2), 'from': a[0]})
    assert btoken.balanceOf(a[1]) == 1999999999999000000


def test_weth_gateway_burn(weth):
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    im = a[0].deploy(BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0))
    oracle = a[0].deploy(BetaOracleUniswapV2, weth, ZERO, 3600)
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(weth)
    btoken = BToken.at(betaBank.bTokens(weth))
    gateway = a[0].deploy(WETHGateway, btoken)
    weth.deposit({'value': mathval(5), 'from': a[0]})
    weth.approve(btoken, 2**256-1, {'from': a[0]})
    btoken.mint(a[1], mathval(2), {'from': a[0]})
    assert btoken.balanceOf(a[1]) == 1999999999999000000
    with brownie.reverts('ERC20: transfer amount exceeds allowance'):
        gateway.burn(a[1], mathval(1), {'from': a[1]})
    btoken.approve(gateway, 2**256-1, {'from': a[1]})
    assert a.at(SEVEN, force=True).balance() == 0
    gateway.burn(SEVEN, mathval(1), {'from': a[1]})
    assert a.at(SEVEN, force=True).balance() == mathval(1)
