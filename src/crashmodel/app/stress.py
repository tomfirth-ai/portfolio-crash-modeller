"""Running the visitor's splits through a crash: the step between their session and the words.

It decides which splits can be run, turns each holding into its model's returns after the fund's
charges, runs each split through the engine, and gathers what the Stress-test page explains: the
path and the fall, which holdings drove the fall, and what the fall would have been with the share
returns counted in dollars rather than pounds.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace

from crashmodel.app.splits import Slot, Split, display_names
from crashmodel.data.catalogue import HOLDINGS_BY_ID, HoldingId
from crashmodel.data.models import IndexModel
from crashmodel.data.panel import Panel
from crashmodel.engine.attribution import fall_contributions
from crashmodel.engine.charges import after_yearly_charge
from crashmodel.engine.drawdown import CrashResult
from crashmodel.engine.episodes import Episode, EpisodeRun, missing_holdings, run_episode
from crashmodel.engine.months import MonthlySeries
from crashmodel.engine.portfolio import Rebalancing


@dataclass(frozen=True, kw_only=True)
class SplitOutcome:
    """How one split came through one crash, or why it could not be run.

    Attributes:
        split: The split, under a name no other split shares.
        slot: Its position, which fixes its colour.
        run: Its path through the crash and how it came through, or ``None`` if it could not be
            run.
        missing: The holdings it has that have no data for the crash.
        fetch_failed: Whether that is because their data could not be fetched just now.
        drivers: For a split that fell, each holding's gain from the high to the bottom, as a
            fraction of the high; they add up to minus the fall.
        shares_in_dollars: For a split holding shares priced in dollars, how it would have come
            through with their returns counted in US dollars rather than pounds, which shows what
            the pound's moves against the dollar did; otherwise ``None``. Global indexes are priced
            in dollars but hold UK and other non-US companies, so for them this is approximate.
    """

    split: Split
    slot: int
    run: EpisodeRun[HoldingId] | None
    missing: tuple[HoldingId, ...] = ()
    fetch_failed: bool = False
    drivers: Mapping[HoldingId, float] = field(default_factory=dict)
    shares_in_dollars: CrashResult | None = None


def runnable(slots: Sequence[Slot]) -> list[tuple[int, Split]]:
    """Return each included split that adds up to 100, with its position, under a unique name."""
    return [
        (position, replace(slot.split, name=name))
        for position, (slot, name) in enumerate(zip(slots, display_names(slots), strict=True))
        if slot.included and slot.split.is_complete
    ]


def models_held(slots: Sequence[Slot]) -> frozenset[IndexModel]:
    """Return the models that the splits to be run hold, so only their data is loaded."""
    return frozenset(
        HOLDINGS_BY_ID[holding].model for _, split in runnable(slots) for holding in split.weights()
    )


def unavailable_holdings(slots: Sequence[Slot], panel: Panel) -> list[HoldingId]:
    """Return the holdings of the splits to be run whose data could not be fetched, once each."""
    held = [holding for _, split in runnable(slots) for holding in split.weights()]
    return [
        holding
        for holding in dict.fromkeys(held)
        if HOLDINGS_BY_ID[holding].model in panel.unavailable
    ]


def outcomes(
    slots: Sequence[Slot],
    episode: Episode,
    panel: Panel,
    rebalancing: Rebalancing = Rebalancing.MONTHLY,
) -> list[SplitOutcome]:
    """Run each included split that adds up to 100 through a crash, noting any that lack data.

    Each split is named so that no two share a name, and keeps the position that fixes its colour.
    """
    return [
        _outcome(split, position, episode, panel, rebalancing)
        for position, split in runnable(slots)
    ]


def _outcome(
    split: Split, slot: int, episode: Episode, panel: Panel, rebalancing: Rebalancing
) -> SplitOutcome:
    weights = split.weights()
    returns = _after_charges(weights, panel.returns)
    missing = tuple(missing_holdings(episode, weights, returns))
    if missing:
        fetch_failed = any(
            HOLDINGS_BY_ID[holding].model in panel.unavailable for holding in missing
        )
        return SplitOutcome(
            split=split, slot=slot, run=None, missing=missing, fetch_failed=fetch_failed
        )
    run = run_episode(episode, weights, returns, rebalancing)
    fall = run.result.fall
    return SplitOutcome(
        split=split,
        slot=slot,
        run=run,
        drivers={} if fall is None else fall_contributions(run.path, fall),
        shares_in_dollars=_with_shares_in_dollars(weights, returns, episode, panel, rebalancing),
    )


def _after_charges(
    weights: Mapping[HoldingId, float], by_model: Mapping[IndexModel, MonthlySeries]
) -> dict[HoldingId, MonthlySeries]:
    """Each holding's returns from its model, after the fund's yearly charge."""
    held = ((holding, HOLDINGS_BY_ID[holding]) for holding in weights)
    return {
        holding: after_yearly_charge(by_model[entry.model], entry.yearly_charge)
        for holding, entry in held
        if entry.model in by_model
    }


def _with_shares_in_dollars(
    weights: Mapping[HoldingId, float],
    returns: Mapping[HoldingId, MonthlySeries],
    episode: Episode,
    panel: Panel,
    rebalancing: Rebalancing,
) -> CrashResult | None:
    in_dollars = _after_charges(weights, panel.dollar_returns)
    if not in_dollars:
        return None
    mixed = {**returns, **in_dollars}
    if missing_holdings(episode, weights, mixed):
        return None
    return run_episode(episode, weights, mixed, rebalancing).result
