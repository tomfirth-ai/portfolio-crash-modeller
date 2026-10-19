from datetime import date
from decimal import Decimal

import pytest

from crashmodel.app.presenters import holdings
from crashmodel.app.presenters.holdings import (
    MODEL_DEFINITIONS,
    MODEL_WORDS,
    holding_help,
    holding_kind,
    holding_label,
    holding_name,
    short_name,
)
from crashmodel.data.catalogue import CATALOGUE, FTSE_ALL_WORLD, HOLDINGS_BY_ID, Fund, Holding
from crashmodel.data.models import MODEL_KINDS, AssetKind, IndexModel
from crashmodel.engine.months import Month

EXCHANGE_TRADED = Holding(
    id="xmpl",
    index=FTSE_ALL_WORLD,
    fund=Fund(
        provider="Vanguard",
        name="Example All-World UCITS ETF Acc",
        ticker="XMPL",
        yearly_charge=Decimal("0.15"),
        launched=Month(2019, 7),
        documented=date(2026, 7, 28),
    ),
)
INDEX_FUND = Holding(
    id="example_index_fund",
    index=FTSE_ALL_WORLD,
    fund=Fund(
        provider="Vanguard",
        name="Example All-World Index Fund C Acc",
        ticker=None,
        yearly_charge=Decimal("0.2"),
        launched=Month(2014, 9),
        documented=date(2026, 2, 1),
    ),
)
"""Made-up funds, so these tests do not depend on what the catalogue lists."""


@pytest.fixture(autouse=True)
def example_funds(monkeypatch: pytest.MonkeyPatch) -> None:
    catalogue = {**HOLDINGS_BY_ID, EXCHANGE_TRADED.id: EXCHANGE_TRADED, INDEX_FUND.id: INDEX_FUND}
    monkeypatch.setattr(holdings, "HOLDINGS_BY_ID", catalogue)


def test_every_label_and_name_says_it_is_modelled() -> None:
    assert holding_label("sp500") == "S&P 500 (modelled): US shares"
    assert holding_label("xmpl") == (
        "XMPL: Example All-World UCITS ETF Acc, tracking FTSE All-World (modelled): world shares, "
        "including emerging markets"
    )
    assert holding_label("example_index_fund") == (
        "Example All-World Index Fund C Acc, tracking FTSE All-World (modelled): world shares, "
        "including emerging markets"
    )
    assert holding_name("xmpl") == "XMPL (modelled)"
    assert holding_name("example_index_fund") == "Example All-World Index Fund C Acc (modelled)"


def test_a_short_name_is_the_ticker_or_else_the_name() -> None:
    assert (short_name("xmpl"), short_name("example_index_fund")) == (
        "XMPL",
        "Example All-World Index Fund C Acc",
    )
    assert short_name("msci_world") == "MSCI World"


def test_an_index_with_a_short_name_keeps_its_full_name_in_the_picker() -> None:
    """So that a search for any word of the index's name finds the index as well as its funds."""
    assert holding_label("ftse_gilts_all_stocks") == (
        "FTSE Actuaries UK Conventional Gilts All Stocks (modelled): UK government bonds"
    )
    assert holding_name("ftse_gilts_all_stocks") == "FTSE All Stocks gilts (modelled)"


def test_a_funds_help_gives_its_index_model_charge_and_launch() -> None:
    assert holding_help("xmpl") == (
        f"Tracks the FTSE All-World index. {MODEL_DEFINITIONS[IndexModel.GLOBAL_LARGE]} Its "
        "ongoing charge of 0.15% a year, from its key information document of 28 July 2026, is "
        "taken off. Launched in July 2019."
    )


def test_an_index_bears_no_charges() -> None:
    assert holding_help("sonia").endswith("No charges are taken off.")


def test_every_model_is_explained_and_every_holding_has_a_kind() -> None:
    assert set(MODEL_DEFINITIONS) == set(IndexModel)
    assert {holding_kind(holding) for holding in HOLDINGS_BY_ID} == {"Shares", "Bonds", "Cash"}


def test_every_model_says_what_it_holds_in_plain_words() -> None:
    assert set(MODEL_WORDS) == set(IndexModel)


def holdings_found_by(search: str) -> set[str]:
    """What Streamlit's picker lists first: the labels holding what is typed, ignoring case."""
    return {holding.id for holding in CATALOGUE if search in holding_label(holding.id).casefold()}


def holdings_of(kind: AssetKind) -> set[str]:
    return {holding.id for holding in CATALOGUE if MODEL_KINDS[holding.model] is kind}


def test_searching_for_cash_or_bonds_finds_exactly_the_holdings_of_that_kind() -> None:
    assert holdings_found_by("cash") == holdings_of(AssetKind.CASH)
    assert holdings_found_by("bonds") == holdings_of(AssetKind.BONDS)


def test_searching_for_shares_finds_every_share_holding() -> None:
    """Some bond funds' class names, such as "Accumulation Shares", match too."""
    assert holdings_of(AssetKind.SHARES) <= holdings_found_by("shares")
