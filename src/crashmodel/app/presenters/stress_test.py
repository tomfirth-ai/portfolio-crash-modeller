"""What the Stress-test page says about each split in each crash.

Every figure comes from the engine. This module turns the results into sentences that say exactly
what each number is measured from, a comparison table and a chart of the value of £100.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from crashmodel.app.presenters.blocks import BLOCK_NAMES_IN_TEXT, block_list
from crashmodel.app.presenters.format import month_name, months, percent, pounds
from crashmodel.app.splits import Split
from crashmodel.data.blocks import Block
from crashmodel.data.french import Vintage
from crashmodel.data.panel import Panel
from crashmodel.engine.drawdown import CrashResult, Fall
from crashmodel.engine.episodes import (
    COVID,
    GLOBAL_FINANCIAL_CRISIS,
    Episode,
    missing_holdings,
    run_episode,
)
from crashmodel.engine.months import MonthlySeries

TITLE = "Stress-test"
INTRODUCTION = (
    "How each split would have come through real crashes, in pounds, if it had been kept at its "
    "weights every month. Every split starts with £100."
)
EXAMPLES_NOTE = "These four splits are examples to show how it works. They are not advice."
CRASH_PICKER = "Crash"
OFFLINE_BANNER = (
    "Share prices could not be fetched just now, so splits holding shares have no results. "
    "Bonds and cash are stored with the app, so those splits still do."
)
TRY_AGAIN = "Try again"
FETCHING = "Fetching share prices..."
TABLE_HEADING = "Side by side"
CHART_HEADING = "What £100 became"
DATA_HEADING = "Where the data comes from"
CAVEAT = (
    "These figures are in pounds before inflation, with no costs, fees or taxes. They use "
    "month-end values, so a fall within a month could have been deeper. Getting back to an "
    "earlier high in pounds is not the same as getting back your spending power."
)
BANK_OF_ENGLAND_CREDIT = (
    "UK government bonds are worked out from the Bank of England's 10-year par gilt yield, "
    "using Swinkels' published bond return method, and cash earns the Bank of England's Bank "
    "Rate. Bank of England data: contains public sector information licensed under the Open "
    "Government Licence v3.0."
)
CHART_X_TITLE = "Month end"
CHART_Y_TITLE = "Value of £100 (£)"
CHART_SPLIT = "Split"
CHART_MONTH = "Month end"
CHART_VALUE = "Value (£)"

EPISODE_NAMES = {
    GLOBAL_FINANCIAL_CRISIS.key: "2007-09 financial crisis",
    COVID.key: "2020 Covid crash",
}
EPISODE_STORIES = {
    GLOBAL_FINANCIAL_CRISIS.key: (
        "Banks' losses on US mortgage debt froze lending in August 2007 and turned into a global "
        "crisis after Lehman Brothers failed in September 2008. Measured from June 2007, the "
        "crash phase runs to June 2009, and recovery is judged by June 2012."
    ),
    COVID.key: (
        "Lockdowns in early 2020 caused the sharpest fall in output on record. Measured from "
        "December 2019, the crash phase runs to June 2020, and recovery is judged by December "
        "2024. Rising interest rates in 2022 hit bonds hard within that time."
    ),
}

COLUMNS = ("Split", "Worst fall", "Months to the bottom", "Months to get back", "£100 became")


@dataclass(frozen=True, kw_only=True)
class SplitOutcome:
    """How one split came through one crash, or why it could not be run.

    Attributes:
        split: The split.
        slot: Its position, which fixes its colour.
        values: Its value at each month end, or ``None`` if it could not be run.
        result: Its fall and recovery, or ``None`` if it could not be run.
        missing: The blocks it holds that have no data for the crash.
    """

    split: Split
    slot: int
    values: MonthlySeries | None
    result: CrashResult | None
    missing: tuple[Block, ...]


@dataclass(frozen=True, kw_only=True)
class CrashCard:
    """One split's story in words."""

    title: str
    slot: int
    sentences: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class ChartPoint:
    """One split's value at one month end, for the chart."""

    split: str
    month: str
    value: float


@dataclass(frozen=True, kw_only=True)
class ValueChartView:
    """The chart of the value of £100 through a crash."""

    points: tuple[ChartPoint, ...]
    splits: tuple[str, ...]
    slots: tuple[int, ...]
    x_title: str = CHART_X_TITLE
    y_title: str = CHART_Y_TITLE
    split_title: str = CHART_SPLIT
    month_title: str = CHART_MONTH
    value_title: str = CHART_VALUE


def outcomes(splits: Sequence[Split], episode: Episode, panel: Panel) -> list[SplitOutcome]:
    """Run each split that adds up to 100 through a crash, noting any that lack data."""
    results: list[SplitOutcome] = []
    for slot, split in enumerate(splits):
        if not split.is_complete:
            continue
        weights = split.weights()
        missing = tuple(missing_holdings(episode, weights, panel.returns))
        if missing:
            results.append(
                SplitOutcome(split=split, slot=slot, values=None, result=None, missing=missing)
            )
            continue
        run = run_episode(episode, weights, panel.returns)
        results.append(
            SplitOutcome(split=split, slot=slot, values=run.values, result=run.result, missing=())
        )
    return results


def card(outcome: SplitOutcome, episode: Episode) -> CrashCard:
    """Tell one split's story through a crash in plain sentences."""
    name = outcome.split.name
    if outcome.result is None:
        sentences: tuple[str, ...] = (
            f"{name} holds {block_list(list(outcome.missing))}, and that data could not be "
            "fetched just now.",
        )
    else:
        ending = (
            f"£100 at the start was worth {pounds(outcome.result.end_value)} by "
            f"{month_name(episode.end)}."
        )
        fall = outcome.result.fall
        if fall is None:
            sentences = (f"{name} did not fall at any month end during the crash.", ending)
        else:
            sentences = (*_fall_sentences(name, fall, episode), ending)
    return CrashCard(title=name, slot=outcome.slot, sentences=sentences)


def _fall_sentences(name: str, fall: Fall, episode: Episode) -> tuple[str, ...]:
    from_start = fall.peak == episode.start
    high = "the start" if from_start else "its high"
    back_to = "where it started" if from_start else "that high"
    if fall.months_to_recover is None:
        recovery = f"had not got back to {back_to} by {month_name(episode.end)}"
    else:
        recovery = f"took another {months(fall.months_to_recover)} to get back to {back_to}"
    sentences = [
        f"{name} fell {percent(fall.depth)} at worst.",
        f"It hit bottom {months(fall.months_to_bottom)} after {high} and {recovery}.",
    ]
    if fall.still_falling:
        crash_end = month_name(episode.crash_end)
        sentences.append(f"It was still at its lowest when the crash phase ended in {crash_end}.")
    if fall.deeper_later is not None:
        sentences.append(f"It later fell further, to {percent(fall.deeper_later)} below {high}.")
    return tuple(sentences)


def table_row(outcome: SplitOutcome, episode: Episode) -> dict[str, str]:
    """One split's figures for the comparison table, keyed by column heading."""
    name = outcome.split.name
    if outcome.result is None:
        cells = (name, "No data", "", "", "")
    elif outcome.result.fall is None:
        cells = (name, "Did not fall", "", "", pounds(outcome.result.end_value))
    else:
        fall = outcome.result.fall
        back = (
            f"Not by {month_name(episode.end)}"
            if fall.months_to_recover is None
            else str(fall.months_to_recover)
        )
        cells = (
            name,
            percent(fall.depth),
            str(fall.months_to_bottom),
            back,
            pounds(outcome.result.end_value),
        )
    return dict(zip(COLUMNS, cells, strict=True))


def chart_view(results: Sequence[SplitOutcome]) -> ValueChartView:
    """The value of £100 in each split that could be run, month by month."""
    drawn = [outcome for outcome in results if outcome.values is not None]
    points = tuple(
        ChartPoint(split=outcome.split.name, month=f"{month}-01", value=value)
        for outcome in drawn
        if outcome.values is not None
        for month, value in outcome.values.items()
    )
    return ValueChartView(
        points=points,
        splits=tuple(outcome.split.name for outcome in drawn),
        slots=tuple(outcome.slot for outcome in drawn),
    )


def share_credit(vintages: Mapping[Block, Vintage]) -> str:
    """Credit the share data, naming the monthly update each file comes from."""
    updates = "; ".join(
        f"{BLOCK_NAMES_IN_TEXT[block]}: the {vintages[block].database} update of "
        f"{month_name(vintages[block].month)}"
        for block in Block
        if block in vintages
    )
    return (
        "Share returns come from the Kenneth R. French Data Library"
        f"{f' ({updates})' if updates else ''}, fetched when the app runs and converted to pounds "
        "at month-end exchange rates from the Federal Reserve's H.10 release, which is public "
        "domain."
    )
