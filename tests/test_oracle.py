import pytest
import brownie
from brownie import (
    a, chain, BetaOracleUniswapV2, MockExternalOracle, MockUniswapV2Factory, MockUniswapV2Pair
)


ZERO = '0x0000000000000000000000000000000000000000'

# Mocking arbitrary addresses
WETH = '0x4de688DF50200AaAFada86898330Fc9aB2E6F4CC'
TOKENA = '0x2A62FFe59b76e9672ed17A4362Fe4246839B9067'
TOKENB = '0x5237eB109C66125C63907b91ac1473dF8A4768b6'


def mathval(val):
    return int(val * 1000000) * 10**12


def test_oracle_weth():
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, ZERO, 3600)
    assert oracle.getAssetETHPrice(WETH).return_value == 2**112
    assert oracle.getAssetETHValue(WETH, mathval(100)).return_value == mathval(100)


def test_oracle_from_external_oracle():
    ext = a[0].deploy(MockExternalOracle)
    factory = a[0].deploy(MockUniswapV2Factory)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, factory, 3600)
    ext.setETHPrice(TOKENA, 3*2**111)  # 1.5 ETH per token
    oracle.setExternalOracle([TOKENA], ext, {'from': a[0]})
    assert oracle.getAssetETHPrice(TOKENA).return_value == 3*2**111
    assert oracle.getAssetETHValue(TOKENA, mathval(100)).return_value == mathval(150)
    with brownie.reverts('updatePriceFromPair/uninitialized'):
        oracle.getAssetETHPrice(TOKENB)
    with brownie.reverts('updatePriceFromPair/uninitialized'):
        oracle.getAssetETHValue(TOKENB, mathval(100))
    with brownie.reverts('getPair/no-pair'):
        oracle.initPriceFromPair(TOKENB)


def test_oracle_price0():
    factory = a[0].deploy(MockUniswapV2Factory)
    pair = a[0].deploy(MockUniswapV2Pair)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, factory, 3600)
    factory.setPair(TOKENA, WETH, pair)
    pair.setReserves(100, 50)
    with brownie.reverts('updatePriceFromPair/uninitialized'):
        oracle.getAssetETHPrice(TOKENA)
    oracle.initPriceFromPair(TOKENA)
    with brownie.reverts('updatePriceFromPair/no-price'):
        oracle.getAssetETHPrice(TOKENA)
    chain.sleep(1800)
    with brownie.reverts('updatePriceFromPair/no-price'):
        oracle.getAssetETHPrice(TOKENA)
    chain.sleep(1800)
    assert oracle.getAssetETHPrice(TOKENA).return_value == 2**111
    assert oracle.getAssetETHValue(TOKENA, mathval(100)).return_value == mathval(50)
    chain.sleep(1800)
    assert oracle.getAssetETHPrice(TOKENA).return_value == 2**111
    assert oracle.getAssetETHValue(TOKENA, mathval(100)).return_value == mathval(50)
    pair.setReserves(100, 75)
    chain.sleep(5400)
    # average price = (0.5*1 + 0.75*3) / 4 = 0.6875
    assert float(oracle.getAssetETHPrice(TOKENA).return_value) == pytest.approx(2**112 * 6875 // 10000, rel=1e-3)
    assert (
        float(oracle.getAssetETHValue(TOKENA, mathval(10000)).return_value) ==
        pytest.approx(mathval(6875), rel=1e-3)
    )


def test_oracle_price1():
    factory = a[0].deploy(MockUniswapV2Factory)
    pair = a[0].deploy(MockUniswapV2Pair)
    oracle = a[0].deploy(BetaOracleUniswapV2, WETH, factory, 3600)
    factory.setPair(TOKENB, WETH, pair)
    pair.setReserves(100, 50)
    with brownie.reverts('updatePriceFromPair/uninitialized'):
        oracle.getAssetETHPrice(TOKENB)
    oracle.initPriceFromPair(TOKENB)
    with brownie.reverts('updatePriceFromPair/no-price'):
        oracle.getAssetETHPrice(TOKENB)
    chain.sleep(1800)
    with brownie.reverts('updatePriceFromPair/no-price'):
        oracle.getAssetETHPrice(TOKENB)
    chain.sleep(1800)
    assert oracle.getAssetETHPrice(TOKENB).return_value == 2**113
    assert oracle.getAssetETHValue(TOKENB, mathval(100)).return_value == mathval(200)
    chain.sleep(1800)
    assert oracle.getAssetETHPrice(TOKENB).return_value == 2**113
    assert oracle.getAssetETHValue(TOKENB, mathval(100)).return_value == mathval(200)
    pair.setReserves(100, 80)
    chain.sleep(5400)
    # average price = (2*1 + 1.25*3) / 4 = 1.4375
    assert float(oracle.getAssetETHPrice(TOKENB).return_value) == pytest.approx(2**112 * 14375 // 10000, rel=1e-3)
    assert (
        float(oracle.getAssetETHValue(TOKENB, mathval(10000)).return_value) ==
        pytest.approx(mathval(14375), rel=1e-3)
    )
