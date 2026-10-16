import re
from datetime import date
from decimal import Decimal
from importlib.resources import files

import pytest

from crashmodel.app.presenters.holdings import holding_label
from crashmodel.data.catalogue import (
    CATALOGUE,
    FTSE_ALL_WORLD,
    FUND_COLUMNS,
    FUND_FILE,
    HOLDINGS_BY_ID,
    INDEXES,
    PROVIDERS,
    S_AND_P_500,
    TRACKED_INDEXES,
    Fund,
    Holding,
    parse_funds,
)
from crashmodel.data.models import IndexModel
from crashmodel.engine.months import Month
from tools.check_hygiene import contains_isin
from tools.policy import FUND_CATALOGUE
from tools.privacy_scan import is_numbers_only


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


HEADER = ",".join(FUND_COLUMNS)
ETF_LINE = "S&P 500,Vanguard,Example S&P 500 UCITS ETF,XMPL,0.07,2019-05,2026-01-01"
INDEX_FUND_LINE = "FTSE All-World,HSBC,Example All-World Index Fund C Acc,,0.20,2014-09,2026-02-01"


def test_the_fund_list_is_read_one_fund_a_line() -> None:
    etf, index_fund = parse_funds(f"{HEADER}\n{ETF_LINE}\n{INDEX_FUND_LINE}\n")
    assert etf == Holding(
        id="xmpl",
        index=S_AND_P_500,
        fund=Fund(
            provider="Vanguard",
            name="Example S&P 500 UCITS ETF",
            ticker="XMPL",
            yearly_charge=Decimal("0.07"),
            launched=Month(2019, 5),
            documented=date(2026, 1, 1),
        ),
    )
    assert (index_fund.id, index_fund.index) == (
        "example_all_world_index_fund_c_acc",
        FTSE_ALL_WORLD,
    )
    assert fund_of(index_fund).ticker is None


@pytest.mark.parametrize(
    ("text", "message"),
    [
        pytest.param("", "must start with the header", id="empty"),
        pytest.param("index,name\n", "must start with the header", id="header"),
        pytest.param(f"{HEADER}\nS&P 500,Vanguard\n", "funds.csv:2: expected 7 fields", id="short"),
        pytest.param(
            f"{HEADER}\n{ETF_LINE.replace('S&P 500', 'Nasdaq-100')}",
            "funds.csv:2: 'Nasdaq-100' is not an index listed here",
            id="index",
        ),
        pytest.param(
            f"{HEADER}\n{ETF_LINE.replace('Vanguard', 'Example')}",
            "funds.csv:2: 'Example' is not a listed provider",
            id="provider",
        ),
        pytest.param(
            f"{HEADER}\n{ETF_LINE.replace('0.07', '7bp')}",
            "funds.csv:2: expected a charge in percent",
            id="charge",
        ),
        pytest.param(
            f"{HEADER}\n{ETF_LINE.replace('2019-05', 'May 2019')}",
            "funds.csv:2: expected a month",
            id="launch",
        ),
        pytest.param(
            f"{HEADER}\n{ETF_LINE.replace('2026-01-01', '2026-02-30')}",
            "funds.csv:2: day is out of range",
            id="document date",
        ),
    ],
)
def test_a_malformed_fund_list_is_refused_with_the_line_at_fault(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        parse_funds(text)


def test_the_fund_list_has_the_shape_the_privacy_scan_expects() -> None:
    """Only a list of exactly this shape has its public names left out of the privacy scan."""
    text = files("crashmodel.data").joinpath(FUND_FILE).read_text(encoding="utf-8")
    assert f"src/crashmodel/data/{FUND_FILE}" == FUND_CATALOGUE
    assert is_numbers_only(FUND_CATALOGUE, text)


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
    assert ("ETF" in fund.name) is (fund.ticker is not None)
    assert fund.ticker is not None or any(word in fund.name for word in ("Fund", "Trust"))
    assert 0 < fund.yearly_charge < LARGEST_PLAUSIBLE_CHARGE
    assert fund.launched <= Month.of(date.today())
    assert fund.documented <= date.today()
    assert holding.index in TRACKED_INDEXES


@pytest.mark.parametrize("holding", CATALOGUE, ids=lambda holding: holding.id)
def test_no_line_holds_an_isin(holding: Holding) -> None:
    """Fund identifiers stay out of the repository, as the hygiene check requires elsewhere."""
    fields = [holding.id, holding.index.name]
    if holding.fund is not None:
        fields += [holding.fund.name, holding.fund.ticker or "", holding.fund.provider]
    assert not any(contains_isin(field) for field in fields)


@pytest.mark.parametrize("holding", FUNDS_ONLY, ids=lambda holding: holding.id)
def test_every_funds_label_names_its_index_so_a_search_for_the_index_finds_it(
    holding: Holding,
) -> None:
    assert holding.index.name.casefold() in holding_label(holding.id).casefold()


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
        assert funds == sorted(funds, key=str.casefold)
        assert all(holding.fund is not None for holding in group[1:])
