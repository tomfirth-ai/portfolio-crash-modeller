"""Every building block's monthly returns in pounds, ready for the engine.

UK government bonds and cash come from the open series stored with the app. Shares come from the
French library files fetched at runtime, converted from dollars at the stored month-end rates. A
share block whose file could not be fetched is listed as unavailable, so a split holding it can say
why it has no result instead of failing.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from crashmodel.data.blocks import SHARE_BLOCKS, Block
from crashmodel.data.french import DEVELOPED_MARKETS, US_MARKET, FrenchFile, MarketReturns, Vintage
from crashmodel.data.reference_data import CASH_RETURN, GILT_YIELD, USD_PER_GBP, stored
from crashmodel.engine.bonds import par_bond_returns
from crashmodel.engine.currency import to_home_currency
from crashmodel.engine.months import MonthlySeries

SHARE_FILES: Mapping[Block, FrenchFile] = {
    Block.GLOBAL_SHARES: DEVELOPED_MARKETS,
    Block.US_SHARES: US_MARKET,
}


@dataclass(frozen=True, kw_only=True)
class Panel:
    """The monthly returns in pounds of every block that has data.

    Attributes:
        returns: Each available block's monthly returns in pounds, as decimals.
        unavailable: Blocks whose data could not be fetched.
        vintages: For share blocks with data, which monthly update of the library it comes from.
        dollar_returns: For share blocks with data, their returns in US dollars, before
            conversion into pounds.
    """

    returns: Mapping[Block, MonthlySeries]
    unavailable: frozenset[Block]
    vintages: Mapping[Block, Vintage]
    dollar_returns: Mapping[Block, MonthlySeries] = field(default_factory=dict)


def stored_returns() -> dict[Block, MonthlySeries]:
    """Return the blocks built only from data stored with the app: UK bonds and cash."""
    return {Block.UK_BONDS: par_bond_returns(stored(GILT_YIELD)), Block.CASH: stored(CASH_RETURN)}


def build_panel(markets: Mapping[Block, MarketReturns | None]) -> Panel:
    """Combine the stored blocks with whichever share files could be fetched.

    Args:
        markets: For each share block, its fetched returns in dollars, or ``None`` if the
            file could not be fetched.
    """
    usd_per_gbp = stored(USD_PER_GBP)
    returns = stored_returns()
    vintages: dict[Block, Vintage] = {}
    dollar_returns: dict[Block, MonthlySeries] = {}
    for block in SHARE_BLOCKS:
        market = markets.get(block)
        if market is not None:
            returns[block] = to_home_currency(market.returns, usd_per_gbp)
            vintages[block] = market.vintage
            dollar_returns[block] = market.returns
    return Panel(
        returns=returns,
        unavailable=frozenset(SHARE_BLOCKS - returns.keys()),
        vintages=vintages,
        dollar_returns=dollar_returns,
    )
