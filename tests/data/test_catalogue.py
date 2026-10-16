import re
from datetime import date
from decimal import Decimal

import pytest

from crashmodel.app.presenters.holdings import holding_label
from crashmodel.data.catalogue import (
    CATALOGUE,
    HOLDINGS_BY_ID,
    INDEXES,
    PROVIDERS,
    S_AND_P_500,
    TRACKED_INDEXES,
    Fund,
    Holding,
)
from crashmodel.data.models import IndexModel
from crashmodel.engine.months import Month
from tools.check_hygiene import contains_isin


def test_every_holding_has_its_own_id() -> None:
    assert len(HOLDINGS_BY_ID) == len(CATALOGUE)


def test_every_model_can_be_held_directly() -> None:
    assert {holding.model for holding in INDEXES} == set(IndexModel)
    assert all(holding.fund is None and holding.yearly_charge == 0 for holding in INDEXES)


def test_a_funds_charge_reaches_the_engine_as_a_fraction() -> None:
    fund = Fund(
        provider="Vanguard",
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


FUNDS_ONLY = [holding for holding in CATALOGUE if holding.fund is not None]
TICKER = re.compile(r"[A-Z0-9]{3,5}", re.ASCII)
LARGEST_PLAUSIBLE_CHARGE = Decimal(2)
"""Index funds and ETFs charge well under 2% a year; anything above is a typing slip."""


def fund_of(holding: Holding) -> Fund:
    assert holding.fund is not None
    return holding.fund


@pytest.mark.parametrize("holding", FUNDS_ONLY, ids=lambda holding: holding.id)
def test_every_fund_line_holds_plausible_facts_from_a_listed_provider(holding: Holding) -> None:
    fund = fund_of(holding)
    assert fund.provider in PROVIDERS
    assert fund.ticker is None or TICKER.fullmatch(fund.ticker)
    assert 0 < fund.yearly_charge < LARGEST_PLAUSIBLE_CHARGE
    assert fund.launched <= Month.of(fund.documented)
    assert fund.documented <= date.today()
    assert holding.index in TRACKED_INDEXES


@pytest.mark.parametrize("holding", CATALOGUE, ids=lambda holding: holding.id)
def test_no_line_holds_an_isin(holding: Holding) -> None:
    """Fund identifiers stay out of the repository, as the hygiene check requires elsewhere."""
    fields = [holding.id, holding.index.name]
    if holding.fund is not None:
        fields += [holding.fund.name, holding.fund.ticker or "", holding.fund.provider]
    assert not any(contains_isin(field) for field in fields)


def test_each_fund_is_listed_once_and_every_label_is_its_own() -> None:
    """The picker tells options apart by their labels, so two may never share one."""
    names = [fund_of(holding).name for holding in FUNDS_ONLY]
    assert len(set(names)) == len(names)
    labels = [holding_label(holding.id) for holding in CATALOGUE]
    assert len(set(labels)) == len(labels)


def test_the_picker_lists_each_index_then_the_funds_tracking_it_alphabetically() -> None:
    positions = [TRACKED_INDEXES.index(holding.index) for holding in CATALOGUE]
    assert positions == sorted(positions)
    for index in TRACKED_INDEXES:
        group = [holding for holding in CATALOGUE if holding.index == index]
        funds = [fund_of(holding).name for holding in group if holding.fund is not None]
        assert funds == sorted(funds)
        assert all(holding.fund is not None for holding in group[1:])
