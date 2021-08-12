from brownie import (
    a,
    chain,
    interface,
    BetaBank,
    BToken,
    BetaConfig,
    BetaOracleUniswapV2,
    BetaInterestModelV1,
    MockExternalOracle,
    ERC20Contract,
    MockExternalOracle,
    WETHGateway,
    BTokenDeployer,
    BetaRunnerUniswapV3,
)
from math import ceil, floor

ZERO = "0x0000000000000000000000000000000000000000"
FEE = 500
TICK_SPACING = 60
FEE_SIZE = 3


def mathval(val):
    return int(val * 1000000) * 10 ** 12


def get_min_tick(tick_spacing):
    return ceil(-887272 / tick_spacing) * tick_spacing


def get_max_tick(tick_spacing):
    return floor(887272 / tick_spacing) * tick_spacing


def encode_path(path, fees):
    assert len(path) == len(fees) + 1
    encoded = "0x"
    for i in range(len(fees)):
        encoded += path[i][2:]  # remove 0x from address
        hex_fee = "{0:x}".format(fees[i])
        encoded += "0" * (2 * FEE_SIZE - len(hex_fee)) + hex_fee  # pad and base 16
    encoded += path[len(path) - 1][2:]
    return encoded.lower()


def generate_params(token_a, token_b):
    token0, token1 = (
        (token_a, token_b) if token_a.lower() < token_b.lower() else (token_b, token_a)
    )
    return (
        token0,
        token1,
        FEE,
        get_min_tick(TICK_SPACING),
        get_max_tick(TICK_SPACING),
        mathval(40),
        mathval(40),
        0,
        0,
        a[9].address,
        chain.time() + 100,
    )


def main():
    factory = interface.IUniswapV3Factory("0x1F98431c8aD98523631AE4a59f267346ea31F984")
    nft = interface.INonFungiblePositionManager(
        "0xC36442b4a4522E871399CD717aBDD847Ab11FE88"
    )
    weth = interface.IWETH("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
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
    ctoken = a[0].deploy(ERC20Contract, "My Collateral Token Name", "CMYSYM")
    dtoken = a[0].deploy(ERC20Contract, "My D Token Name", "DMYSYM")
    tokens = [utoken, ctoken, dtoken]
    for token in tokens:
        token.mint(a[0], mathval(1000000))
        token.mint(a[1], mathval(1000000))
        token.mint(a[9], mathval(1000000))
        ext.setETHPrice(token, 2 ** 112, {"from": a[0]})
    oracle.setExternalOracle(tokens, ext, {"from": a[0]})
    betaBank.initialize(a[0], a[0].deploy(BTokenDeployer), oracle, config, im)
    betaBank.create(utoken)
    betaBank.create(weth)
    btoken = BToken.at(betaBank.bTokens(utoken))
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[0]})
    btoken.mint(a[0], mathval(1000), {"from": a[0]})
    utoken.approve(btoken, 2 ** 256 - 1, {"from": a[1]})
    ctoken.approve(betaBank, 2 ** 256 - 1, {"from": a[1]})

    bweth = BToken.at(betaBank.bTokens(weth))
    gw = a[0].deploy(WETHGateway, bweth)
    gw.mint(a[0], {"value": mathval(75), "from": a[0]})
    weth.deposit({"value": mathval(200), "from": a[9]})

    config.setCollFactors([ctoken, weth], [mathval(0.8), mathval(0.8)], {"from": a[0]})
    rt2 = a[0].deploy(
        BetaRunnerUniswapV3,
        betaBank,
        weth,
        factory,
        "0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54",
    )
    betaBank.setRunnerWhitelists([rt2], True, {"from": a[0]})

    utoken.approve(rt2, 2 ** 256 - 1, {"from": a[1]})
    ctoken.approve(rt2, 2 ** 256 - 1, {"from": a[1]})

    # approve runner and nft position manager
    for token in tokens + [weth]:
        for addr in [rt2, nft]:
            token.approve(addr, 2 ** 256 - 1, {"from": a[9]})

    # create uniswap v3 pool, initialize, and mint initial supply
    pools = [
        (utoken, ctoken),
        (utoken, weth),
        (ctoken, weth),
        (dtoken, weth),
        (dtoken, ctoken),
    ]
    for token0, token1 in pools:
        factory.createPool(token0, token1, FEE, {"from": a[0]})
        pool = interface.IUniswapV3Pool(factory.getPool(token0, token1, FEE))
        pool.initialize(str(2 ** 96), {"from": a[9]})  # init with price 1
        liquidity_params = generate_params(token0.address, token1.address)
        nft.mint(liquidity_params, {"from": a[9]})

    # short, path.length == 2
    # collateral - ctoken, underlying - utoken -> ctoken
    path1, fee1 = [utoken.address, ctoken.address], [FEE]
    rt2.short(
        [2 ** 256 - 1, mathval(2), mathval(10), encode_path(path1, fee1), 0],
        {"from": a[1]},
    )
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 0))
    rt2.close(
        [0, 2 ** 256 - 1, mathval(10), encode_path(path1, fee1), mathval(100)],
        {"from": a[1]},
    )
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 0))

    # collateral - weth.address, underlying - utoken -> weth
    path2, fee2 = [utoken.address, weth.address], [FEE]
    rt2.short(
        [2 ** 256 - 1, mathval(2), mathval(10), encode_path(path2, fee2), 0],
        {"value": mathval(10), "from": a[1]},
    )
    print(a[1].balance())
    print(betaBank.positions(a[1], 1))
    rt2.close(
        [1, 2 ** 256 - 1, mathval(10), encode_path(path2, fee2), mathval(10)],
        {"from": a[1]},
    )
    print(a[1].balance())
    print(betaBank.positions(a[1], 1))

    # collateral - ctoken, underlying - weth.address -> ctoken
    path3, fee3 = [weth.address, ctoken.address], [FEE]
    rt2.short(
        [2 ** 256 - 1, mathval(2), mathval(10), encode_path(path3, fee3), 0],
        {"from": a[1]},
    )
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 2))
    rt2.close(
        [2, 2 ** 256 - 1, mathval(10), encode_path(path3, fee3), mathval(100)],
        {"from": a[1]},
    )
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 2))

    # collateral - ctoken, underlying - utoken -> weth.address -> ctoken
    path4, fee4 = [utoken.address, weth.address, ctoken.address], [FEE, FEE]
    rt2.short(
        [2 ** 256 - 1, mathval(2), mathval(10), encode_path(path4, fee4), 0],
        {"from": a[1]},
    )
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 3))
    rt2.close(
        [3, 2 ** 256 - 1, mathval(10), encode_path(path4, fee4), mathval(100)],
        {"from": a[1]},
    )
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 3))

    # multi-path, hit for loop, collateral - ctoken, underlying - utoken -> utoken -> weth -> dtoken -> ctoken
    path5, fee5 = [utoken.address, weth.address, dtoken.address, ctoken.address], [
        FEE,
        FEE,
        FEE,
    ]
    rt2.short(
        [2 ** 256 - 1, mathval(2), mathval(10), encode_path(path5, fee5), 0],
        {"from": a[1]},
    )
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 4))
    rt2.close(
        [4, 2 ** 256 - 1, mathval(10), encode_path(path5, fee5), mathval(100)],
        {"from": a[1]},
    )
    print(ctoken.balanceOf(a[1]))
    print(betaBank.positions(a[1], 4))
