from datetime import date
from decimal import Decimal

import pytest

from crashmodel.data.catalogue import (
    CATALOGUE,
    HOLDINGS_BY_ID,
    INDEXES,
    S_AND_P_500,
    Fund,
    Holding,
)
from crashmodel.data.models import IndexModel
from crashmodel.engine.months import Month


def test_every_holding_has_its_own_id() -> None:
    assert len(HOLDINGS_BY_ID) == len(CATALOGUE)


def test_every_model_can_be_held_directly() -> None:
    assert {holding.model for holding in INDEXES} == set(IndexModel)
    assert all(holding.fund is None and holding.yearly_charge == 0 for holding in INDEXES)


def test_a_funds_charge_reaches_the_engine_as_a_fraction() -> None:
    fund = Fund(
        name="Example",
        ticker="XMPL",
        yearly_charge=Decimal("0.07"),
        launched=Month(2019, 5),
        documented=date(2026, 1, 1),
    )
    holding = Holding(id="xmpl", index=S_AND_P_500, fund=fund)
    assert holding.yearly_charge == pytest.approx(0.0007)
    assert holding.model is IndexModel.US_LARGE


@pytest.mark.parametrize("holding_id", ["VWRP", "s&p", "two words", ""])
def test_an_id_that_could_not_be_part_of_a_widget_key_is_refused(holding_id: str) -> None:
    with pytest.raises(ValueError, match="lower-case"):
        Holding(id=holding_id, index=S_AND_P_500)
