"""What the Stress-test page says about each split in each crash.

Every figure comes from the engine. This module turns the results into sentences that say exactly
what each number is measured from, a comparison table and a chart of the value of £100.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from crashmodel.app.journey import STRESS_TEST
from crashmodel.app.presenters.format import (
    listed,
    month_name,
    months,
    percent,
    pounds,
    pounds_and_pence,
)
from crashmodel.app.presenters.holdings import holding_list, holding_name, short_name
from crashmodel.app.presenters.names import markdown_text
from crashmodel.app.splits import Slot, display_names, example_slots
from crashmodel.app.stress import SplitOutcome
from crashmodel.data.catalogue import HoldingId
from crashmodel.data.french import PORTFOLIO_FILES, PortfolioFile, Vintage
from crashmodel.engine.drawdown import CrashResult, Fall
from crashmodel.engine.episodes import COVID, DOT_COM, GLOBAL_FINANCIAL_CRISIS, Episode
from crashmodel.engine.portfolio import STARTING_VALUE, Rebalancing

TITLE = STRESS_TEST.title
INTRODUCTION = (
    "How each split would have come through real crashes, in pounds. Every split starts with £100."
)
EXAMPLES_NOTE = "These four splits are examples to show how it works. They are not advice."
CHANGE_SPLITS = "Change the splits"
NO_SPLITS = "There is no split to test yet. Switch one on, and make it add up to 100%."
CRASH_PICKER = "Crash"
MANAGEMENT_PICKER = "How each split is managed"
MANAGEMENT_NAMES = {
    Rebalancing.MONTHLY.value: "Kept at its percentages",
    Rebalancing.NEVER.value: "Left alone",
}
MANAGEMENT_HELP = (
    "Kept at its percentages: put back to them at the end of every month, much as ready-made "
    "multi-asset funds keep a fixed mix. Left alone: bought once and never changed, so whatever "
    "does well grows to a larger share."
)
TRY_AGAIN = "Try again"
FETCHING = "Fetching share data..."
TABLE_HEADING = "Side by side"
CHART_HEADING = "What £100 became"
DATA_HEADING = "Where the data comes from"
SIMULATED = (
    "Simulated past performance: these figures come from models, not from any fund's or index's "
    "own returns."
)
CAVEAT = (
    "These figures are in pounds before inflation. Each fund's ongoing charge is taken off; tax on "
    "dividends, dealing costs and platform charges are not. Income a fund pays out is counted as "
    "reinvested. They use month-end values, so a fall within a month could have been deeper. "
    "Getting back to an earlier high in pounds is not the same as getting back your spending power."
)
BANK_OF_ENGLAND_CREDIT = (
    "UK gilts are modelled from the Bank of England's 10-year par gilt yield, using Swinkels' "
    "published bond return method, and sterling cash earns the Bank of England's Bank Rate. Bank "
    "of England data: contains public sector information licensed under the Open Government "
    "Licence v3.0."
)
CHART_X_TITLE = "Month end"
CHART_Y_TITLE = "Value of £100 (£)"
CHART_SPLIT = "Split"
CHART_MONTH = "Month end"
CHART_VALUE = "Value (£)"

EPISODE_NAMES = {
    DOT_COM.key: "2000-03 dot-com crash",
    GLOBAL_FINANCIAL_CRISIS.key: "2007-09 financial crisis",
    COVID.key: "2020 Covid crash",
}
EPISODE_STORIES = {
    DOT_COM.key: (
        "Technology shares had soared in the late 1990s. The bubble burst in March 2000, and the "
        "fall deepened through the US recession of 2001, the September 2001 attacks and the "
        "accounting scandals of 2002. Measured from February 2000, the crash phase runs to March "
        "2003, when the Iraq war began, and recovery is judged by February 2005."
    ),
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

MINIMUM_HOLDINGS_TO_EXPLAIN = 2
"""A split in one holding needs no breakdown of its fall."""
NOTHING = pounds_and_pence(0)

COLUMNS = (
    "Split",
    "Worst fall in the crash",
    "Months to the bottom",
    "Months to get back",
    "£100 became",
)


@dataclass(frozen=True, kw_only=True)
class CrashCard:
    """One split's story in words: what happened, then why, then anything to bear in mind."""

    title: str
    sentences: tuple[str, ...]
    why: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        """What happened, as one paragraph."""
        return " ".join(self.sentences)

    @property
    def why_text(self) -> str:
        """Why it happened, as one paragraph, which may be empty."""
        return " ".join(self.why)

    @property
    def notes_text(self) -> str:
        """What to bear in mind, as one paragraph, which may be empty."""
        return " ".join(self.notes)


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


def management_name(value: str) -> str:
    """What a way of managing a split is called, such as "Left alone"."""
    return MANAGEMENT_NAMES[value]


def episode_name(key: str) -> str:
    """What the crash with this key is called, such as "2020 Covid crash"."""
    return EPISODE_NAMES[key]


def examples_note(slots: Sequence[Slot]) -> str | None:
    """Point out that the splits are only examples, while they still are."""
    return EXAMPLES_NOTE if tuple(slots) == example_slots() else None


def left_out_note(slots: Sequence[Slot]) -> str | None:
    """Say which included splits are left out because they do not add up to 100, if any."""
    names = display_names(slots)
    sentences = [
        f"{markdown_text(name)} is left out, because it adds up to {slot.split.total}%, not 100%."
        for slot, name in zip(slots, names, strict=True)
        if slot.included and not slot.split.is_complete
    ]
    return " ".join(sentences) or None


def offline_banner(unavailable: Sequence[HoldingId]) -> str:
    """Say which holdings' data could not be fetched, and that other splits are unaffected."""
    return (
        f"The share data behind {holding_list(unavailable)} could not be fetched just now, so "
        "splits holding them have no results. Splits without them are not affected."
    )


def card(outcome: SplitOutcome, episode: Episode) -> CrashCard:
    """Tell one split's story through a crash in plain sentences, as Markdown."""
    name = markdown_text(outcome.split.name)
    if outcome.run is None:
        reason = (
            "that data could not be fetched just now"
            if outcome.fetch_failed
            else "there is no data for every month of this crash"
        )
        missing = holding_list(outcome.missing)
        sentences: tuple[str, ...] = (f"{name} holds {missing}, and {reason}.",)
    else:
        result = outcome.run.result
        ending = (
            f"£100 at the start was worth {pounds(result.end_value)} by {month_name(episode.end)}."
        )
        fall = result.fall
        if fall is None:
            crash_end = month_name(episode.crash_end)
            sentences = (
                f"{name} did not fall at any month end in the crash phase, to {crash_end}.",
                ending,
            )
        else:
            sentences = (*_fall_sentences(name, fall, episode), ending)
    return CrashCard(
        title=name,
        sentences=sentences,
        why=_why(outcome, episode),
        notes=_launch_notes(outcome),
    )


def _launch_notes(outcome: SplitOutcome) -> tuple[str, ...]:
    """Name the funds launched after the crash began, whose figures are modelled like the rest."""
    if not outcome.launched_late:
        return ()
    names = [short_name(holding) for holding in outcome.launched_late]
    launches = [month_name(month) for month in outcome.launched_late.values()]
    if len(names) == 1:
        return (
            f"{names[0]} was launched after this crash began, in {launches[0]}. Its figures, like "
            "every figure here, come from a model of the index it tracks, after its charge.",
        )
    return (
        f"{listed(names)} were launched after this crash began, in {listed(launches)}. Their "
        "figures, like every figure here, come from models of the indexes they track, after their "
        "charges.",
    )


def _why(outcome: SplitOutcome, episode: Episode) -> tuple[str, ...]:
    fall = None if outcome.run is None else outcome.run.result.fall
    drivers = None if fall is None else _drivers_sentence(outcome.drivers, _high(fall, episode))
    reasons = (drivers, _pound_sentence(outcome))
    return tuple(reason for reason in reasons if reason is not None)


def _high(fall: Fall, episode: Episode) -> str:
    """Name the high a fall is measured from, as the card does: the start, or a later high."""
    return "the start" if fall.peak == episode.start else "its high"


def _drivers_sentence(drivers: Mapping[HoldingId, float], high: str) -> str | None:
    """Say how much each holding lost or made back on the way down, per £100 at the high.

    Nothing is said for a split of one holding, or when no loss is big enough to show in pence,
    so a fall is never put down to gains alone.
    """
    if len(drivers) < MINIMUM_HOLDINGS_TO_EXPLAIN:
        return None
    ordered = sorted(drivers.items(), key=lambda item: abs(item[1]), reverse=True)
    amounts = [
        (holding, share, pounds_and_pence(abs(share) * STARTING_VALUE))
        for holding, share in ordered
    ]
    lost = [
        f"{holding_name(holding)} lost {amount}"
        for holding, share, amount in amounts
        if share < 0 and amount != NOTHING
    ]
    made_back = [
        f"{holding_name(holding)} made back {amount}"
        for holding, share, amount in amounts
        if share > 0 and amount != NOTHING
    ]
    if not lost:
        return None
    return (
        f"Of every £100 it had at {high}, {listed(lost + made_back)} on the way down to its low "
        "in the crash phase."
    )


def _pound_sentence(outcome: SplitOutcome) -> str | None:
    """Say how the fall would have differed with the share returns counted in dollars."""
    if outcome.run is None or outcome.shares_in_dollars is None:
        return None
    actual, in_dollars = _depth(outcome.run.result), _depth(outcome.shares_in_dollars)
    if percent(actual) == percent(in_dollars):
        return None
    start = "With its shares' returns counted in dollars rather than pounds, it would"
    effect = "cushioned it" if in_dollars > actual else "made it worse"
    if not in_dollars:
        return (
            f"{start} not have fallen in the crash phase: the pound's moves against the dollar "
            "made it worse."
        )
    rather = f" rather than {percent(actual)}" if actual else ""
    return (
        f"{start} have fallen {percent(in_dollars)} at worst in the crash phase{rather}: the "
        f"pound's moves against the dollar {effect}."
    )


def _depth(result: CrashResult) -> float:
    return 0.0 if result.fall is None else result.fall.depth


def _fall_sentences(name: str, fall: Fall, episode: Episode) -> tuple[str, ...]:
    high = _high(fall, episode)
    back_to = "where it started" if fall.peak == episode.start else "that high"
    if fall.months_to_recover is None:
        recovery = f"had not got back to {back_to} by {month_name(episode.end)}"
    else:
        wait = fall.months_to_recover
        another = "another month" if wait == 1 else f"another {months(wait)}"
        recovery = f"took {another} to get back to {back_to}"
    sentences = [
        f"{name} fell {percent(fall.depth)} at worst in the crash phase.",
        f"It hit bottom {months(fall.months_to_bottom)} after {high} and {recovery}.",
    ]
    if fall.still_falling:
        crash_end = month_name(episode.crash_end)
        sentences.append(f"It was still at its lowest when the crash phase ended in {crash_end}.")
    if fall.deeper_later is not None:
        before = "" if fall.recovery is None else ", and before it got back"
        sentences.append(
            f"After the crash phase{before}, it fell further, to {percent(fall.deeper_later)} "
            f"below {high}."
        )
    return tuple(sentences)


def table_row(outcome: SplitOutcome, episode: Episode) -> dict[str, str]:
    """One split's figures for the comparison table, as Markdown keyed by column heading."""
    name = markdown_text(outcome.split.name)
    if outcome.run is None:
        cells = (name, "No data", "", "", "")
    elif (fall := outcome.run.result.fall) is None:
        cells = (name, "None", "", "", pounds(outcome.run.result.end_value))
    else:
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
            pounds(outcome.run.result.end_value),
        )
    return dict(zip(COLUMNS, cells, strict=True))


def chart_view(results: Sequence[SplitOutcome]) -> ValueChartView:
    """The value of £100 in each split that could be run, month by month."""
    drawn = [(outcome, outcome.run) for outcome in results if outcome.run is not None]
    points = tuple(
        ChartPoint(split=outcome.split.name, month=f"{month}-01", value=value)
        for outcome, run in drawn
        for month, value in run.values.items()
    )
    return ValueChartView(
        points=points,
        splits=tuple(outcome.split.name for outcome, _ in drawn),
        slots=tuple(outcome.slot for outcome, _ in drawn),
    )


def share_credit(vintages: Mapping[PortfolioFile, Vintage]) -> str:
    """Credit the share data, naming the monthly update each file comes from."""
    updates = "; ".join(
        f"{file.name}: the {vintages[file].database} update of {month_name(vintages[file].month)}"
        for file in PORTFOLIO_FILES
        if file in vintages
    )
    return (
        "Share models are built from the Kenneth R. French Data Library's portfolios of companies "
        f"grouped by size{f' ({updates})' if updates else ''}, fetched when the app runs and "
        "converted to pounds at month-end exchange rates from the Federal Reserve's H.10 release, "
        "which is public domain."
    )
