"""Each share model from synthetic portfolio files whose combinations can be worked by hand."""

import pytest

from crashmodel.data.french import (
    DEVELOPED_BY_SIZE,
    EMERGING_BY_SIZE,
    US_BY_SIZE,
    PortfolioFile,
    Portfolios,
    parse_portfolios,
)
from crashmodel.data.models import (
    MODEL_KINDS,
    SHARE_MODEL_FILES,
    AssetKind,
    IndexModel,
    share_model_returns,
)
from crashmodel.engine.months import Month
from tests.data.french_portfolio_text import FIRST_MONTH, Cell, Values, portfolio_text


def us(column: str, _month: Month) -> Cell:
    """The largest tenth holds 400 firms worth 10 each and the next 200 worth 10 each."""
    if column == "Hi 10":
        return 1.0, 400, 10
    if column == "9-Dec":
        return 6.0, 200, 10
    return -50.0, 1000, 1


def developed(column: str, _month: Month) -> Cell:
    """Big portfolios worth 1000, 1000 and 2000; small ones worth 100 each, all losing half."""
    big = {"BIG LoBM": (1.0, 10, 100), "ME2 BM2": (2.0, 10, 100), "BIG HiBM": (3.0, 10, 200)}
    return big.get(column, (-50.0, 10, 10))


def emerging(column: str, _month: Month) -> Cell:
    """Big portfolios worth 500, 250 and 250, all gaining 6%; small ones as in developed."""
    big = {"BIG LoBM": (6.0, 10, 50), "ME2 BM2": (6.0, 10, 25), "BIG HiBM": (6.0, 10, 25)}
    return big.get(column, (-50.0, 10, 10))


def fetched(file: PortfolioFile, values: Values, start: Month = FIRST_MONTH) -> Portfolios:
    return parse_portfolios(portfolio_text(file, values=values, start=start), file)


FILES = {
    US_BY_SIZE: fetched(US_BY_SIZE, us),
    DEVELOPED_BY_SIZE: fetched(DEVELOPED_BY_SIZE, developed),
    EMERGING_BY_SIZE: fetched(EMERGING_BY_SIZE, emerging, start=FIRST_MONTH + -3),
}


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        # The 500 largest: Hi 10's 400 (worth 4000) and 100 of 9-Dec's 200 (worth 1000):
        # (4000 * 1% + 1000 * 6%) / 5000.
        (IndexModel.US_LARGE, 0.02),
        # Big only: (1000 * 1% + 1000 * 2% + 2000 * 3%) / 4000.
        (IndexModel.DEVELOPED_LARGE, 0.0225),
        # Developed big (90 on 4000) and emerging big (60 on 1000): 150 / 5000.
        (IndexModel.GLOBAL_LARGE, 0.03),
        # Every size: the small portfolios add 600 of value that loses 300: (150 - 300) / 5600.
        (IndexModel.GLOBAL_ALL_CAP, -150 / 5600),
    ],
)
def test_each_share_model_weights_its_portfolios_by_market_value(
    model: IndexModel, expected: float
) -> None:
    returns = share_model_returns(model, FILES)
    assert returns.values == pytest.approx((expected,) * len(returns))


def test_a_model_from_two_files_covers_the_months_both_cover() -> None:
    returns = share_model_returns(IndexModel.GLOBAL_LARGE, FILES)
    assert (returns.start, returns.end) == (FIRST_MONTH, FIRST_MONTH + 20)


def test_every_share_model_names_the_files_it_needs() -> None:
    shares = {model for model, kind in MODEL_KINDS.items() if kind is AssetKind.SHARES}
    assert set(SHARE_MODEL_FILES) == shares
    for model, files in SHARE_MODEL_FILES.items():
        share_model_returns(model, {file: FILES[file] for file in files})


def test_every_model_is_a_kind_of_investment() -> None:
    assert set(MODEL_KINDS) == set(IndexModel)


def test_bond_and_cash_models_are_not_built_from_share_files() -> None:
    with pytest.raises(KeyError):
        share_model_returns(IndexModel.UK_GILTS, FILES)
