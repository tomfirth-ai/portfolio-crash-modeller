"""The index models a fund can be linked to, and how each share model is built.

A model gives the monthly total returns of a kind of index, built from data the app may use. Share
models combine the French library's portfolios of companies grouped by size, weighted by market
value each month (ADR 0005). Bond and cash models come from the open series stored with the app.
What each model is called, and which real indexes it stands for, lives with the catalogue and the
presenters; this module only builds them.
"""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from crashmodel.data.french import (
    BIG,
    DEVELOPED_BY_SIZE,
    EMERGING_BY_SIZE,
    PORTFOLIO_FILES,
    SMALL,
    US_BY_SIZE,
    US_SIZE_DECILES,
    PortfolioFile,
    Portfolios,
)
from crashmodel.engine.indexes import SizedPortfolio, cap_weighted, largest_firms
from crashmodel.engine.months import MonthlySeries


class IndexModel(StrEnum):
    """A model of an index, which funds tracking that index are linked to."""

    US_LARGE = "us_large"
    """The 500 largest US companies, as the S&P 500 holds."""
    DEVELOPED_LARGE = "developed_large"
    """The large and mid-sized companies of developed countries, as MSCI World holds."""
    GLOBAL_LARGE = "global_large"
    """The large and mid-sized companies of developed and emerging countries, as FTSE All-World
    holds."""
    GLOBAL_ALL_CAP = "global_all_cap"
    """Companies of every size in developed and emerging countries, as FTSE Global All Cap holds."""
    UK_GILTS_ALL = "uk_gilts_all"
    """UK government bonds of every term, as the FTSE Actuaries All Stocks gilt index holds."""
    UK_GILTS_SHORT = "uk_gilts_short"
    """UK government bonds with up to 5 years left to run."""
    UK_GILTS_LONG = "uk_gilts_long"
    """UK government bonds with over 15 years left to run."""
    STERLING_CASH = "sterling_cash"
    """Cash earning SONIA, compounded daily, with Bank Rate before SONIA began in 1997."""


class AssetKind(StrEnum):
    """The broad kind of investment a model is."""

    SHARES = "shares"
    BONDS = "bonds"
    CASH = "cash"


MODEL_KINDS: Mapping[IndexModel, AssetKind] = {
    IndexModel.US_LARGE: AssetKind.SHARES,
    IndexModel.DEVELOPED_LARGE: AssetKind.SHARES,
    IndexModel.GLOBAL_LARGE: AssetKind.SHARES,
    IndexModel.GLOBAL_ALL_CAP: AssetKind.SHARES,
    IndexModel.UK_GILTS_ALL: AssetKind.BONDS,
    IndexModel.UK_GILTS_SHORT: AssetKind.BONDS,
    IndexModel.UK_GILTS_LONG: AssetKind.BONDS,
    IndexModel.STERLING_CASH: AssetKind.CASH,
}

LARGEST_US_FIRMS = 500
"""How many companies the S&P 500 holds."""

type FetchedFiles = Mapping[PortfolioFile, Portfolios]


def _largest_us(files: FetchedFiles) -> MonthlySeries:
    return largest_firms(_held(files, US_BY_SIZE, US_SIZE_DECILES), LARGEST_US_FIRMS)


def _developed_large(files: FetchedFiles) -> MonthlySeries:
    return cap_weighted(_held(files, DEVELOPED_BY_SIZE, BIG))


def _global_large(files: FetchedFiles) -> MonthlySeries:
    return cap_weighted(_held(files, DEVELOPED_BY_SIZE, BIG) + _held(files, EMERGING_BY_SIZE, BIG))


def _global_all_cap(files: FetchedFiles) -> MonthlySeries:
    every_size = BIG + SMALL
    return cap_weighted(
        _held(files, DEVELOPED_BY_SIZE, every_size) + _held(files, EMERGING_BY_SIZE, every_size)
    )


def _held(
    files: FetchedFiles, file: PortfolioFile, columns: tuple[str, ...]
) -> list[SizedPortfolio]:
    return [files[file].portfolios[column] for column in columns]


@dataclass(frozen=True)
class _Recipe:
    files: tuple[PortfolioFile, ...]
    build: Callable[[FetchedFiles], MonthlySeries]


_SHARE_RECIPES: Mapping[IndexModel, _Recipe] = {
    IndexModel.US_LARGE: _Recipe((US_BY_SIZE,), _largest_us),
    IndexModel.DEVELOPED_LARGE: _Recipe((DEVELOPED_BY_SIZE,), _developed_large),
    IndexModel.GLOBAL_LARGE: _Recipe((DEVELOPED_BY_SIZE, EMERGING_BY_SIZE), _global_large),
    IndexModel.GLOBAL_ALL_CAP: _Recipe((DEVELOPED_BY_SIZE, EMERGING_BY_SIZE), _global_all_cap),
}

SHARE_MODEL_FILES: Mapping[IndexModel, tuple[PortfolioFile, ...]] = {
    model: recipe.files for model, recipe in _SHARE_RECIPES.items()
}
"""The French files each share model is built from."""


def share_model_returns(model: IndexModel, files: FetchedFiles) -> MonthlySeries:
    """Return a share model's monthly total returns in US dollars.

    Args:
        model: A share model, one of :data:`SHARE_MODEL_FILES`.
        files: The fetched files, including every file the model needs.

    Raises:
        KeyError: If ``model`` is not a share model, or a file it needs is missing.
    """
    return _SHARE_RECIPES[model].build(files)


def files_for(models: Iterable[IndexModel]) -> tuple[PortfolioFile, ...]:
    """Return the French files the share models among ``models`` need, once each, in order."""
    needed = {file for model in models for file in SHARE_MODEL_FILES.get(model, ())}
    return tuple(file for file in PORTFOLIO_FILES if file in needed)
