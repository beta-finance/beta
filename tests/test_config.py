import brownie
from brownie import a, chain, BetaConfig


ZERO = '0x0000000000000000000000000000000000000000'
TOKENA = '0x2A62FFe59b76e9672ed17A4362Fe4246839B9067'
TOKENB = '0x5237eB109C66125C63907b91ac1473dF8A4768b6'
TOKENC = '0xC56407E38c9900c404D3d24Cb0Ac50b022Af2d16'


def mathval(val):
    return int(val * 1000000) * 10**12


def test_config_governor():
    config = a[0].deploy(BetaConfig, a[0], 0)
    assert config.governor() == a[0]
    assert config.pendingGovernor() == ZERO
    with brownie.reverts('setPendingGovernor/not-governor'):
        config.setPendingGovernor(a[1], {'from': a[1]})
    with brownie.reverts('acceptGovernor/not-pending-governor'):
        config.acceptGovernor({'from': a[1]})
    config.setPendingGovernor(a[1], {'from': a[0]})
    assert config.governor() == a[0]
    assert config.pendingGovernor() == a[1]
    with brownie.reverts('acceptGovernor/not-pending-governor'):
        config.acceptGovernor({'from': a[0]})
    config.acceptGovernor({'from': a[1]})
    assert config.governor() == a[1]
    assert config.pendingGovernor() == ZERO
    with brownie.reverts('setPendingGovernor/not-governor'):
        config.setPendingGovernor(a[2], {'from': a[0]})
    config.setPendingGovernor(a[2], {'from': a[1]})
    assert config.governor() == a[1]
    assert config.pendingGovernor() == a[2]


def test_config_reserves():
    config = a[0].deploy(BetaConfig, a[0], 0)
    assert config.reserveBeneficiary() == a[0]
    assert config.reserveRate() == 0
    with brownie.reverts('setReserveInfo/not-governor'):
        config.setReserveInfo(a[1], mathval(0.5), {'from': a[1]})
    with brownie.reverts('setReserveInfo/bad-rate'):
        config.setReserveInfo(a[1], mathval(1.5), {'from': a[0]})
    config.setReserveInfo(a[1], mathval(0.5), {'from': a[0]})
    assert config.reserveBeneficiary() == a[1]
    assert config.reserveRate() == mathval(0.5)


def test_config_reserves_zero_beneficiary():
    config = a[0].deploy(BetaConfig, a[0], 0)
    with brownie.reverts('setReserveInfo/bad-beneficiary'):
        config.setReserveInfo(ZERO, mathval(0.5), {'from': a[0]})
    assert config.reserveBeneficiary() == a[0]
    assert config.reserveRate() == 0


def test_config_collateral_factors():
    config = a[0].deploy(BetaConfig, a[0], 0)
    with brownie.reverts('getCollFactor/no-collateral-factor'):
        assert config.getCollFactor(TOKENA)
    with brownie.reverts('setCollFactors/not-governor'):
        assert config.setCollFactors([TOKENA, TOKENB], [mathval(0.75), mathval(1.00)], {'from': a[1]})
    with brownie.reverts('setCollFactors/bad-length'):
        assert config.setCollFactors([TOKENA], [mathval(0.75), mathval(1.00)], {'from': a[0]})
    with brownie.reverts('setCollFactors/bad-factor-value'):
        assert config.setCollFactors([TOKENA, TOKENB], [mathval(0.75), mathval(1.01)], {'from': a[0]})
    assert config.setCollFactors([TOKENA, TOKENB], [mathval(0.75), mathval(1.00)], {'from': a[0]})
    assert config.getCollFactor(TOKENA) == mathval(0.75)
    assert config.getCollFactor(TOKENB) == mathval(1.00)
    with brownie.reverts('getCollFactor/no-collateral-factor'):
        assert config.getCollFactor(TOKENC)
    assert config.setCollFactors([TOKENB, TOKENC], [mathval(0.85), mathval(1.00)], {'from': a[0]})
    assert config.getCollFactor(TOKENA) == mathval(0.75)
    assert config.getCollFactor(TOKENB) == mathval(0.85)
    assert config.getCollFactor(TOKENC) == mathval(1.00)


def test_config_default_level():
    config = a[0].deploy(BetaConfig, a[0], 0)
    assert config.getRiskLevel(TOKENA) == 0
    with brownie.reverts('getSafetyLTV/no-ltv'):
        assert config.getSafetyLTV(TOKENA)
    with brownie.reverts('getLiquidationLTV/no-ltv'):
        assert config.getLiquidationLTV(TOKENA)
    with brownie.reverts('getKillBountyRate/no-rate'):
        assert config.getKillBountyRate(TOKENA)
    with brownie.reverts('setRiskConfigs/not-governor'):
        config.setRiskConfigs(
            [0, 1],
            [[mathval(0.5), mathval(0.75), mathval(0.05)], [mathval(0.5), mathval(0.75), mathval(0.05)]],
            {'from': a[1]},
        )
    with brownie.reverts('setRiskConfigs/bad-safety-ltv'):
        config.setRiskConfigs(
            [0, 1],
            [[mathval(1.2), mathval(0.75), mathval(0.05)], [mathval(0.5), mathval(0.75), mathval(0.05)]],
            {'from': a[0]},
        )
    with brownie.reverts('setRiskConfigs/bad-liquidation-ltv'):
        config.setRiskConfigs(
            [0, 1],
            [[mathval(0.5), mathval(1.2), mathval(0.05)], [mathval(0.5), mathval(0.75), mathval(0.05)]],
            {'from': a[0]},
        )
    with brownie.reverts('setRiskConfigs/inconsistent-ltv-values'):
        config.setRiskConfigs(
            [0, 1],
            [[mathval(0.75), mathval(0.5), mathval(0.05)], [mathval(0.5), mathval(0.75), mathval(0.05)]],
            {'from': a[0]},
        )
    with brownie.reverts('setRiskConfigs/bad-kill-reward-factor'):
        config.setRiskConfigs(
            [0, 1],
            [[mathval(0.5), mathval(0.75), mathval(1.05)], [mathval(0.5), mathval(0.75), mathval(0.05)]],
            {'from': a[0]},
        )
    config.setRiskConfigs(
        [0, 1],
        [[mathval(0.5), mathval(0.75), mathval(0.05)], [mathval(0.5), mathval(0.75), mathval(0.05)]],
        {'from': a[0]},
    )
    assert config.getSafetyLTV(TOKENA) == mathval(0.5)
    assert config.getLiquidationLTV(TOKENA) == mathval(0.75)
    assert config.getKillBountyRate(TOKENA) == mathval(0.05)


def test_config_level_nondefault():
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0, 1],
        [[mathval(0.5), mathval(0.75), mathval(0.05)], [mathval(0.4), mathval(0.6), mathval(0.04)]],
        {'from': a[0]},
    )
    with brownie.reverts('setRiskLevels/not-governor'):
        config.setRiskLevels([TOKENB], [1], {'from': a[1]})
    config.setRiskLevels([TOKENB], [1], {'from': a[0]})
    assert config.getSafetyLTV(TOKENA) == mathval(0.5)
    assert config.getLiquidationLTV(TOKENA) == mathval(0.75)
    assert config.getKillBountyRate(TOKENA) == mathval(0.05)
    assert config.getSafetyLTV(TOKENB) == mathval(0.4)
    assert config.getLiquidationLTV(TOKENB) == mathval(0.6)
    assert config.getKillBountyRate(TOKENB) == mathval(0.04)


def test_config_level_blacklist():
    config = a[0].deploy(BetaConfig, a[0], 0)
    config.setRiskConfigs(
        [0, 1],
        [[mathval(0.5), mathval(0.75), mathval(0.05)], [mathval(0.4), mathval(0.6), mathval(0.04)]],
        {'from': a[0]},
    )
    with brownie.reverts('setRiskLevels/not-governor'):
        config.setRiskLevels([TOKENB], [1], {'from': a[1]})
    config.setRiskLevels([TOKENA, TOKENB], [1, 2**256-1], {'from': a[0]})
    with brownie.reverts('getRiskLevel/bad-risk-level'):
        config.getRiskLevel(TOKENB)
    assert config.getRiskLevel(TOKENA) == 1
