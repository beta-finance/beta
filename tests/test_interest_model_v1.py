from brownie import a, BetaInterestModelV1


def mathval(val):
    return int(val * 1000000) * 10 ** 12


def test_interest_model_deploy():
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5)
    )
    assert im.initialRate() == 20 * 10 ** 16
    assert im.minRate() == 5 * 10 ** 16
    assert im.maxRate() == 10000 * 10 ** 16
    assert im.adjustRate() == 50 * 10 ** 16
    assert im.initialRate() == 20 * 10 ** 16


def test_interest_model_basic():
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5)
    )
    assert (
        im.getNextInterestRate(mathval(0.30), 100, 0, 1000) == 298263888888888888
    )  # 0% util
    assert (
        im.getNextInterestRate(mathval(0.30), 50, 50, 1000) == 298263888888888888
    )  # 50% util
    assert (
        im.getNextInterestRate(mathval(0.30), 40, 60, 1000) == 299131944444444444
    )  # 60% util
    assert (
        im.getNextInterestRate(mathval(0.30), 35, 65, 1000) == 299565972222222222
    )  # 65% util
    assert (
        im.getNextInterestRate(mathval(0.30), 30, 70, 1000) == 300000000000000000
    )  # 70% util
    assert (
        im.getNextInterestRate(mathval(0.30), 20, 80, 1000) == 300000000000000000
    )  # 80% util
    assert (
        im.getNextInterestRate(mathval(0.30), 15, 85, 1000) == 300868055555555555
    )  # 85% util
    assert (
        im.getNextInterestRate(mathval(0.30), 10, 90, 1000) == 301736111111111111
    )  # 90% util
    assert (
        im.getNextInterestRate(mathval(0.30), 0, 100, 1000) == 303472222222222222
    )  # 100% util


def test_interest_model_day_capped():
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.7)
    )
    assert (
        im.getNextInterestRate(mathval(0.30), 100, 0, 100000) == 90000000000000000
    )  # 0% util
    assert (
        im.getNextInterestRate(mathval(0.30), 50, 50, 100000) == 90000000000000000
    )  # 50% util
    assert (
        im.getNextInterestRate(mathval(0.30), 40, 60, 100000) == 195000000000000000
    )  # 60% util
    assert (
        im.getNextInterestRate(mathval(0.30), 35, 65, 100000) == 247500000000000000
    )  # 65% util
    assert (
        im.getNextInterestRate(mathval(0.30), 30, 70, 100000) == 300000000000000000
    )  # 70% util
    assert (
        im.getNextInterestRate(mathval(0.30), 20, 80, 100000) == 300000000000000000
    )  # 80% util
    assert (
        im.getNextInterestRate(mathval(0.30), 15, 85, 100000) == 474999999999999999
    )  # 85% util
    assert (
        im.getNextInterestRate(mathval(0.30), 10, 90, 100000) == 649999999999999999
    )  # 90% util
    assert (
        im.getNextInterestRate(mathval(0.30), 0, 100, 100000) == 999999999999999999
    )  # 100% util


def test_interest_rate_result_capped():
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5)
    )
    assert im.getNextInterestRate(mathval(0.01), 100, 100, 10) == mathval(0.05)
    assert im.getNextInterestRate(mathval(1000), 100, 100, 10) == mathval(100)


def test_interest_rate_day_capped_extreme():
    im = a[0].deploy(
        BetaInterestModelV1, mathval(0.20), mathval(0.05), mathval(100), mathval(0.5)
    )
    assert im.getNextInterestRate(mathval(0.30), 100, 0, 100000) == mathval(
        0.15
    )  # 0% util
    assert im.getNextInterestRate(mathval(0.30), 50, 50, 100000) == mathval(
        0.15
    )  # 50% util
    assert im.getNextInterestRate(mathval(0.30), 0, 100, 100000) == mathval(
        0.60
    )  # 100% util
