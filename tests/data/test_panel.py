from types import MappingProxyType

import pytest

from crashmodel.data.french import (
    DEVELOPED_BY_SIZE,
    EMERGING_BY_SIZE,
    US_BY_SIZE,
    PortfolioFile,
    Portfolios,
    parse_portfolios,
)
from crashmodel.data.models import IndexModel
from crashmodel.data.panel import build_panel, stored_returns
from crashmodel.data.reference_data import USD_PER_GBP, load
from crashmodel.engine.months import Month
from tests.data.french_portfolio_text import portfolio_text

START = Month(2007, 1)
STORED = {
    IndexModel.UK_GILTS_ALL,
    IndexModel.UK_GILTS_SHORT,
    IndexModel.UK_GILTS_LONG,
    IndexModel.STERLING_CASH,
}


def fetched(file: PortfolioFile, start: Month = START) -> Portfolios:
    return parse_portfolios(portfolio_text(file, start=start), file)


def test_gilts_and_cash_come_from_the_stored_series() -> None:
    """The ladders start once the curve reaches 20 years, short gilts once the 5-year par yield
    has two months, and cash once Bank Rate covers a whole month."""
    stored = stored_returns()
    assert set(stored) == STORED
    starts = {model: returns.start for model, returns in stored.items()}
    assert starts == {
        IndexModel.UK_GILTS_ALL: Month(1992, 4),
        IndexModel.UK_GILTS_LONG: Month(1992, 4),
        IndexModel.UK_GILTS_SHORT: Month(1994, 1),
        IndexModel.STERLING_CASH: Month(1975, 2),
    }


def test_the_stored_models_are_built_once_and_cannot_be_changed() -> None:
    assert stored_returns() is stored_returns()
    assert isinstance(stored_returns(), MappingProxyType)


def test_one_panels_share_models_never_reach_another() -> None:
    build_panel({US_BY_SIZE: fetched(US_BY_SIZE)})
    assert set(build_panel({}).returns) == STORED


def test_share_models_are_converted_to_pounds_at_the_stored_rates() -> None:
    panel = build_panel({US_BY_SIZE: fetched(US_BY_SIZE)})
    rates = load(USD_PER_GBP)
    month = Month(2008, 10)
    dollars = panel.dollar_returns[IndexModel.US_LARGE][month]
    assert panel.returns[IndexModel.US_LARGE][month] == pytest.approx(
        (1 + dollars) * rates[month.previous] / rates[month] - 1
    )
    assert panel.vintages[US_BY_SIZE].month == START + 23


def test_only_models_whose_files_were_asked_for_are_built() -> None:
    panel = build_panel({DEVELOPED_BY_SIZE: fetched(DEVELOPED_BY_SIZE)})
    assert set(panel.returns) == STORED | {IndexModel.DEVELOPED_LARGE}
    assert panel.unavailable == frozenset()


def test_a_model_is_unavailable_when_a_file_it_needs_could_not_be_fetched() -> None:
    panel = build_panel({DEVELOPED_BY_SIZE: fetched(DEVELOPED_BY_SIZE), EMERGING_BY_SIZE: None})
    assert IndexModel.DEVELOPED_LARGE in panel.returns
    assert panel.unavailable == {IndexModel.GLOBAL_LARGE, IndexModel.GLOBAL_ALL_CAP}
    assert set(panel.vintages) == {DEVELOPED_BY_SIZE}


def test_a_model_whose_files_share_no_month_is_unavailable() -> None:
    later = START + 30
    files = {
        DEVELOPED_BY_SIZE: fetched(DEVELOPED_BY_SIZE),
        EMERGING_BY_SIZE: fetched(EMERGING_BY_SIZE, start=later),
    }
    panel = build_panel(files)
    assert IndexModel.GLOBAL_LARGE in panel.unavailable
    assert IndexModel.DEVELOPED_LARGE in panel.returns


def test_without_share_data_gilts_and_cash_still_have_returns() -> None:
    panel = build_panel({})
    assert set(panel.returns) == STORED
    assert panel.unavailable == frozenset()
