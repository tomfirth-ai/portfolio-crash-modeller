"""Running the visitor's splits through a crash: the step between their session and the words.

It decides which splits can be run, runs each one through the engine, and gathers what the
Stress-test page explains: the path and the fall, which holdings drove the fall, and what the fall
would have been had the pound held steady against the dollar.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace

from crashmodel.app.presenters.names import display_names
from crashmodel.app.splits import Slot, Split
from crashmodel.data.blocks import Block
from crashmodel.data.panel import Panel
from crashmodel.engine.attribution import fall_contributions
from crashmodel.engine.drawdown import CrashResult
from crashmodel.engine.episodes import Episode, EpisodeRun, missing_holdings, run_episode
from crashmodel.engine.portfolio import Rebalancing


@dataclass(frozen=True, kw_only=True)
class SplitOutcome:
    """How one split came through one crash, or why it could not be run.

    Attributes:
        split: The split, under a name no other split shares.
        slot: Its position, which fixes its colour.
        run: Its path through the crash and how it came through, or ``None`` if it could not be
            run.
        missing: The blocks it holds that have no data for the crash.
        fetch_failed: Whether that is because their data could not be fetched just now.
        drivers: For a split that fell, each holding's gain from the high to the bottom, as a
            fraction of the high; they add up to minus the fall.
        steady_pound: For a split holding dollar shares, how it would have come through had the
            pound held steady against the dollar; otherwise ``None``.
    """

    split: Split
    slot: int
    run: EpisodeRun[Block] | None
    missing: tuple[Block, ...] = ()
    fetch_failed: bool = False
    drivers: Mapping[Block, float] = field(default_factory=dict)
    steady_pound: CrashResult | None = None


def outcomes(
    slots: Sequence[Slot],
    episode: Episode,
    panel: Panel,
    rebalancing: Rebalancing = Rebalancing.MONTHLY,
) -> list[SplitOutcome]:
    """Run each included split that adds up to 100 through a crash, noting any that lack data.

    Each split is named so that no two share a name, and keeps the position that fixes its colour.
    """
    results: list[SplitOutcome] = []
    for position, (slot, name) in enumerate(zip(slots, display_names(slots), strict=True)):
        if slot.included and slot.split.is_complete:
            split = replace(slot.split, name=name)
            results.append(_outcome(split, position, episode, panel, rebalancing))
    return results


def _outcome(
    split: Split, slot: int, episode: Episode, panel: Panel, rebalancing: Rebalancing
) -> SplitOutcome:
    weights = split.weights()
    missing = tuple(missing_holdings(episode, weights, panel.returns))
    if missing:
        fetch_failed = any(block in panel.unavailable for block in missing)
        return SplitOutcome(
            split=split, slot=slot, run=None, missing=missing, fetch_failed=fetch_failed
        )
    run = run_episode(episode, weights, panel.returns, rebalancing)
    fall = run.result.fall
    return SplitOutcome(
        split=split,
        slot=slot,
        run=run,
        drivers={} if fall is None else fall_contributions(run.path, fall),
        steady_pound=_with_a_steady_pound(weights, episode, panel, rebalancing),
    )


def _with_a_steady_pound(
    weights: Mapping[Block, float], episode: Episode, panel: Panel, rebalancing: Rebalancing
) -> CrashResult | None:
    if not panel.dollar_returns.keys() & weights.keys():
        return None
    returns = {**panel.returns, **panel.dollar_returns}
    if missing_holdings(episode, weights, returns):
        return None
    return run_episode(episode, weights, returns, rebalancing).result
