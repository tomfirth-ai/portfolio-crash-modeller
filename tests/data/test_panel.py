import pytest

from crashmodel.data.blocks import SHARE_BLOCKS, Block
from crashmodel.data.french import MarketReturns, Vintage
from crashmodel.data.panel import SHARE_FILES, build_panel, stored_returns
from crashmodel.data.reference_data import USD_PER_GBP, load
from crashmodel.engine.months import Month, MonthlySeries

VINTAGE = Vintage(month=Month(2008, 12), database="CRSP")
ZERO_DOLLAR_RETURNS = MarketReturns(
    returns=MonthlySeries(Month(2007, 1), (0.0,) * 24), vintage=VINTAGE
)


def test_bonds_and_cash_come_from_the_stored_series() -> None:
    stored = stored_returns()
    assert set(stored) == {Block.UK_BONDS, Block.CASH}
    assert stored[Block.UK_BONDS].start == Month(1994, 1)
    assert stored[Block.CASH].start == Month(1975, 2)


def test_every_share_block_has_a_french_file() -> None:
    assert set(SHARE_FILES) == SHARE_BLOCKS


def test_share_returns_are_converted_to_pounds_at_the_stored_rates() -> None:
    panel = build_panel({Block.US_SHARES: ZERO_DOLLAR_RETURNS, Block.GLOBAL_SHARES: None})
    rates = load(USD_PER_GBP)
    month = Month(2008, 10)
    assert panel.returns[Block.US_SHARES][month] == pytest.approx(
        rates[month.previous] / rates[month] - 1
    )
    assert panel.vintages == {Block.US_SHARES: VINTAGE}
    assert panel.unavailable == {Block.GLOBAL_SHARES}
    assert panel.dollar_returns == {Block.US_SHARES: ZERO_DOLLAR_RETURNS.returns}


def test_without_share_data_bonds_and_cash_still_have_returns() -> None:
    panel = build_panel({})
    assert set(panel.returns) == {Block.UK_BONDS, Block.CASH}
    assert panel.unavailable == SHARE_BLOCKS
