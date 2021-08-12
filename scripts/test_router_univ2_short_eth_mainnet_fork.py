from brownie import (
    a,
    interface,
    BetaBank,
    BToken,
    BetaConfig,
    BetaOracleUniswapV2,
    BetaInterestModelV1,
    BetaRunnerUniswapV2,
    MockExternalOracle,
    ERC20Contract,
    MockExternalOracle,
    WETHGateway,
    BTokenDeployer,
)


ZERO = "0x0000000000000000000000000000000000000000"


def mathval(val):
    return int(val * 1000000) * 10 ** 12


def main():
    factory = interface.IUniswapV2Factory("0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f")
    router = interface.IUniswapV2Router("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")
    weth = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    betaBank = a[0].deploy(BetaBank)
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0], [[mathval(0.33), mathval(0.5), mathval(0.05)]], {"from": a[0]}
    )
    ext = a[0].deploy(MockExternalOracle)
    oracle = a[0].deploy(BetaOracleUniswapV2, weth, ZERO, 3600)
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0), mathval(0), mathval(100), mathval(0)
    )
    utoken = a[0].deploy(ERC20Contract, "My Underlying Token Name", "UMYSYM")
    utoken.mint(a[0], mathval(1000000))
    utoken.mint(a[1], mathval(1000000))
    utoken.mint(a[9], mathval(1000000))
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    ctoken.mint(a[0], mathval(1000000))
    ctoken.mint(a[1], mathval(1000000))
    ctoken.mint(a[9], mathval(1000000))
    ext.setETHPrice(utoken, 2 ** 112, {"from": a[0]})
    ext.setETHPrice(ctoken, 2 ** 112, {"from": a[0]})
    oracle.setExternalOracle([utoken, ctoken], ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.create(weth)
    btoken = BToken.at(betaBank.bTokens(utoken))
    bweth = BToken.at(betaBank.bTokens(weth))
    rt = a[0].deploy(
        BetaRunnerUniswapV2,
        betaBank,
        weth,
        factory,
        "0x96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f",
    )
    betaBank.setRunnerWhitelists([rt], True, {"from": a[0]})
    gw = a[0].deploy(WETHGateway, bweth)
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})
    gw.mint(a[0], {"value": mathval(75), "from": a[0]})
    # create uniswap pool
    factory.createPair(utoken, ctoken, {"from": a[0]})
    factory.createPair(utoken, weth, {"from": a[0]})
    factory.createPair(ctoken, weth, {"from": a[0]})
    utoken.approve(router, 2 ** 256 - 1, {"from": a[9]})
    ctoken.approve(router, 2 ** 256 - 1, {"from": a[9]})
    router.addLiquidity(
        utoken, ctoken, mathval(40), mathval(40), 0, 0, a[9], 1700000000, {"from": a[9]}
    )
    router.addLiquidityETH(
        utoken,
        mathval(40),
        0,
        0,
        a[9],
        1700000000,
        {"value": mathval(40), "from": a[9]},
    )
    router.addLiquidityETH(
        ctoken,
        mathval(40),
        0,
        0,
        a[9],
        1700000000,
        {"value": mathval(40), "from": a[9]},
    )
    config.setCollFactors([ctoken, weth], [mathval(0.8), mathval(0.8)], {"from": a[0]})
    utoken.approve(rt, 2 ** 256 - 1, {"from": a[1]})
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[1]})
    ctoken.approve(rt, 2 ** 256 - 1, {"from": a[1]})
    ctoken.approve(betaBank, 2 ** 256 - 1, {"from": a[1]})
    # collateral - ctoken, underlying - utoken -> ctoken
    rt.short(2 ** 256 - 1, mathval(2), mathval(10), [utoken, ctoken], 0, {"from": a[1]})
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 0))
    rt.close(
        0, 2 ** 256 - 1, mathval(10), [ctoken, utoken], 2 ** 256 - 1, {"from": a[1]}
    )
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 0))
    # collateral - weth, underlying - utoken -> weth
    rt.short(
        2 ** 256 - 1,
        mathval(2),
        mathval(10),
        [utoken, weth],
        0,
        {"value": mathval(10), "from": a[1]},
    )
    print(a[1].balance())
    print(betaBank.positions(a[1], 1))
    rt.close(1, 2 ** 256 - 1, mathval(10), [weth, utoken], mathval(10), {"from": a[1]})
    print(a[1].balance())
    print(betaBank.positions(a[1], 1))
    # collateral - ctoken, underlying - weth -> ctoken
    rt.short(2 ** 256 - 1, mathval(2), mathval(10), [weth, ctoken], 0, {"from": a[1]})
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 2))
    rt.close(2, 2 ** 256 - 1, mathval(10), [ctoken, weth], 2 ** 256 - 1, {"from": a[1]})
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 2))
    # collateral - ctoken, underlying - utoken -> weth -> ctoken
    rt.short(
        2 ** 256 - 1, mathval(2), mathval(10), [utoken, weth, ctoken], 0, {"from": a[1]}
    )
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 3))
    rt.close(
        3,
        2 ** 256 - 1,
        mathval(10),
        [ctoken, weth, utoken],
        2 ** 256 - 1,
        {"from": a[1]},
    )
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 3))
