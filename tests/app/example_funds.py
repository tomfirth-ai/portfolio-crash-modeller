"""Made-up funds tracking the S&P 500, launched around a test crash that starts in June 2007."""

from datetime import date
from decimal import Decimal

import pytest

from crashmodel.app import stress
from crashmodel.app.presenters import holdings
from crashmodel.data.catalogue import HOLDINGS_BY_ID, S_AND_P_500, Fund, Holding
from crashmodel.engine.months import Month


def example_fund(ticker: str, launched: Month) -> Holding:
    """A fund charging 1.2% a year, which is 0.1% a month."""
    fund = Fund(
        provider="Vanguard",
        name=f"Example {ticker} S&P 500 UCITS ETF",
        ticker=ticker,
        yearly_charge=Decimal("1.2"),
        launched=launched,
        documented=date(2026, 1, 1),
    )
    return Holding(id=ticker.lower(), index=S_AND_P_500, fund=fund)


EXAMPLE_FUNDS = (
    example_fund("EARLY", Month(2007, 5)),
    example_fund("START", Month(2007, 6)),
    example_fund("LATE", Month(2007, 8)),
    example_fund("LATER", Month(2007, 9)),
)


def use_example_funds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Add the example funds to the catalogue the app's modules look holdings up in."""
    catalogue = {**HOLDINGS_BY_ID, **{holding.id: holding for holding in EXAMPLE_FUNDS}}
    for module in (stress, holdings):
        monkeypatch.setattr(module, "HOLDINGS_BY_ID", catalogue)
