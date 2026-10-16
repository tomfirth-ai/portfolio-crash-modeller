"""Every index model's monthly returns in pounds, ready for the engine.

UK gilts and sterling cash are built once from the open series stored with the app. Share models
are built from the French library's size portfolio files fetched at runtime, then converted from
dollars at the stored month-end rates. A share model whose files could not all be fetched, or did
not combine, is listed as unavailable, so a split holding it can say why it has no result instead
of failing.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cache
from types import MappingProxyType

from crashmodel.data.french import PortfolioFile, Portfolios, Vintage
from crashmodel.data.gilts import gilt_models, stored_curve_points
from crashmodel.data.models import SHARE_MODEL_FILES, IndexModel, share_model_returns
from crashmodel.data.reference_data import (
    FIVE_YEAR_PAR_YIELD,
    STERLING_CASH_RETURN,
    USD_PER_GBP,
    stored,
)
from crashmodel.engine.currency import to_home_currency
from crashmodel.engine.months import MonthlySeries


@dataclass(frozen=True, kw_only=True)
class Panel:
    """The monthly returns in pounds of every model that has data.

    Attributes:
        returns: Each available model's monthly returns in pounds, as decimals.
        unavailable: Share models whose data could not be fetched or read.
        vintages: For each fetched file, which monthly update of the library it comes from.
        dollar_returns: For share models with data, their returns in US dollars, before
            conversion into pounds.
    """

    returns: Mapping[IndexModel, MonthlySeries]
    unavailable: frozenset[IndexModel]
    vintages: Mapping[PortfolioFile, Vintage]
    dollar_returns: Mapping[IndexModel, MonthlySeries] = field(default_factory=dict)


@cache
def stored_returns() -> Mapping[IndexModel, MonthlySeries]:
    """Return the models built only from data stored with the app: UK gilts and sterling cash.

    The stored files never change while the app runs, so the models are built once.
    """
    cash = stored(STERLING_CASH_RETURN)
    gilts = gilt_models(stored_curve_points(), stored(FIVE_YEAR_PAR_YIELD), cash)
    return MappingProxyType({**gilts, IndexModel.STERLING_CASH: cash})


def build_panel(files: Mapping[PortfolioFile, Portfolios | None]) -> Panel:
    """Combine the stored models with every share model whose files were fetched.

    Args:
        files: Each file that was asked for, with its portfolios, or ``None`` if it could not be
            fetched. A share model that needs a file not asked for is left out: it is neither built
            nor unavailable.
    """
    usd_per_gbp = stored(USD_PER_GBP)
    fetched = {file: portfolios for file, portfolios in files.items() if portfolios is not None}
    returns = dict(stored_returns())
    dollar_returns: dict[IndexModel, MonthlySeries] = {}
    unavailable: set[IndexModel] = set()
    for model, needed in SHARE_MODEL_FILES.items():
        if not files.keys() >= set(needed):
            continue
        built = _built(model, fetched, usd_per_gbp) if fetched.keys() >= set(needed) else None
        if built is None:
            unavailable.add(model)
        else:
            dollar_returns[model], returns[model] = built
    return Panel(
        returns=returns,
        unavailable=frozenset(unavailable),
        vintages={file: portfolios.vintage for file, portfolios in fetched.items()},
        dollar_returns=dollar_returns,
    )


def _built(
    model: IndexModel, fetched: Mapping[PortfolioFile, Portfolios], usd_per_gbp: MonthlySeries
) -> tuple[MonthlySeries, MonthlySeries] | None:
    """Return a share model's returns in dollars and pounds, or ``None`` if it cannot be built."""
    try:
        dollars = share_model_returns(model, fetched)
        return dollars, to_home_currency(dollars, usd_per_gbp)
    except ValueError:
        return None
