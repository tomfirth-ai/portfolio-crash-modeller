"""What each fund and index is called, and what its model is, in plain words.

Every name the app shows for a fund or an index says it is modelled, because no figure is the fund's
or the index's own (ADR 0005).
"""

from collections.abc import Iterable

from crashmodel.app.presenters.format import date_name, listed, month_name
from crashmodel.data.catalogue import HOLDINGS_BY_ID, HoldingId
from crashmodel.data.models import MODEL_KINDS, AssetKind, IndexModel

MODELLED = "(modelled)"

MODEL_DEFINITIONS = {
    IndexModel.US_LARGE: (
        "Modelled as the 500 largest US companies, held in proportion to their market value, with "
        "dividends reinvested."
    ),
    IndexModel.DEVELOPED_LARGE: (
        "Modelled as the large and mid-sized companies of 23 developed countries, including the "
        "US and the UK, held in proportion to their market value, with dividends reinvested."
    ),
    IndexModel.GLOBAL_LARGE: (
        "Modelled as the large and mid-sized companies of developed and emerging countries, held "
        "in proportion to their market value, with dividends reinvested."
    ),
    IndexModel.GLOBAL_ALL_CAP: (
        "Modelled as companies of every size in developed and emerging countries, held in "
        "proportion to their market value, with dividends reinvested."
    ),
    IndexModel.UK_GILTS_ALL: (
        "Modelled as UK government bonds with up to 50 years left to run, each keeping the coupon "
        "it was issued with, valued off the Bank of England's yield curve. Bonds lose value when "
        "interest rates rise and gain when they fall, the longer-dated ones most."
    ),
    IndexModel.UK_GILTS_SHORT: (
        "Modelled as half a 5-year UK government bond, bought new each month at the going yield, "
        "and half cash earning SONIA. Short-dated bonds move little when interest rates change."
    ),
    IndexModel.UK_GILTS_LONG: (
        "Modelled as UK government bonds with 15 to 50 years left to run, each keeping the coupon "
        "it was issued with, valued off the Bank of England's yield curve. Long-dated bonds lose "
        "the most when interest rates rise and gain the most when they fall."
    ),
    IndexModel.STERLING_CASH: (
        "Modelled as cash earning SONIA, the rate banks pay each other overnight, compounded "
        "daily, with the Bank of England's Bank Rate before SONIA began in 1997."
    ),
}

KIND_LABELS = {AssetKind.SHARES: "Shares", AssetKind.BONDS: "Bonds", AssetKind.CASH: "Cash"}


def holding_label(holding_id: HoldingId) -> str:
    """Label a holding in the picker, such as "VWRP: Vanguard FTSE All-World... (modelled)".

    A fund whose name does not say which index it tracks has the index added, so that searching
    the picker for an index finds every fund tracking it.
    """
    holding = HOLDINGS_BY_ID[holding_id]
    fund = holding.fund
    if fund is None:
        return f"{holding.index.name} {MODELLED}"
    name = fund.name if fund.ticker is None else f"{fund.ticker}: {fund.name}"
    if holding.index.name.casefold() not in fund.name.casefold():
        name = f"{name}, tracking {holding.index.name}"
    return f"{name} {MODELLED}"


def holding_name(holding_id: HoldingId) -> str:
    """Name a holding in a sentence or a chart, such as "VWRP (modelled)"."""
    return f"{short_name(holding_id)} {MODELLED}"


def holding_list(holding_ids: Iterable[HoldingId]) -> str:
    """Name holdings in a sentence, such as "VWRP (modelled) and SONIA (modelled)"."""
    return listed([holding_name(holding_id) for holding_id in holding_ids])


def holding_help(holding_id: HoldingId) -> str:
    """Say what a holding's model is and, for a fund, its charge and when it was launched."""
    holding = HOLDINGS_BY_ID[holding_id]
    definition = MODEL_DEFINITIONS[holding.model]
    if holding.fund is None:
        return f"{definition} No charges are taken off."
    fund = holding.fund
    return (
        f"Tracks the {holding.index.name} index. {definition} Its ongoing charge of "
        f"{fund.yearly_charge}% a year, from its key information document of "
        f"{date_name(fund.documented)}, is taken off. Launched in {month_name(fund.launched)}."
    )


def holding_kind(holding_id: HoldingId) -> str:
    """Say what kind of investment a holding is, such as "Shares"."""
    return KIND_LABELS[MODEL_KINDS[HOLDINGS_BY_ID[holding_id].model]]


def short_name(holding_id: HoldingId) -> str:
    """Name a holding as briefly as can be, such as "VWRP" or "S&P 500"."""
    holding = HOLDINGS_BY_ID[holding_id]
    if holding.fund is None:
        return holding.index.short_name or holding.index.name
    return holding.fund.ticker or holding.fund.name
