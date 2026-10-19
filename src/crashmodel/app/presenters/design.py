"""What the Design page says: what each split holds, its total, and what is still needed."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from crashmodel.app.journey import DESIGN
from crashmodel.app.presenters.holdings import KIND_LABELS, holding_kind, holding_name
from crashmodel.app.presenters.names import markdown_text
from crashmodel.app.splits import EXAMPLE_SPLITS, WHOLE, Slot, Split, display_names
from crashmodel.data.catalogue import HoldingId
from crashmodel.data.models import AssetKind

TITLE = DESIGN.title
INTRODUCTION = (
    "Choose up to six funds or indexes for each split, then give each a whole percentage so that "
    "they add up to 100. Every one is modelled from published research and open data: each fund "
    "after its ongoing charge, and each index before any charges. You can compare up to four "
    "splits; switch one off to leave it out. So far there are US, developed-world and world "
    "shares, UK government bonds and sterling cash; more markets are planned."
)
START_OWN = "Start your own"
SHOW_EXAMPLES = "Reset all to the examples"
SESSION_NOTE = (
    "Your splits stay while this tab is open; reloading the page starts again from the examples."
)
INCLUDE = "Include"
NAME = "Name"
TEMPLATE = "Fill from an example"
TEMPLATE_PLACEHOLDER = "Choose an example"
TEMPLATE_NAMES = tuple(split.name for split in EXAMPLE_SPLITS)
HOLDINGS = "Funds and indexes"
HOLDINGS_PLACEHOLDER = "Search by name, ticker or kind, such as bonds"
HOLDINGS_HELP = (
    "Search by ticker, fund, index or kind, such as shares, bonds or cash. Each fund is modelled "
    "from the index it tracks, after its ongoing charge. An index on its own is modelled before "
    "any charges."
)
MAX_HOLDINGS = 6
COMPOSITION_HEADING = "What each split holds"
COMPOSITION_X_TITLE = "Share of £100 (%)"
COMPOSITION_SPLIT = "Split"
COMPOSITION_HOLDING = "Holding"
COMPOSITION_KIND = "Kind"
COMPOSITION_PERCENT = "Share (%)"
NEXT = "Stress-test these splits"
NOTHING_INCLUDED = "Switch on at least one split to stress-test it."
NAME_MAX_CHARACTERS = 30
PERCENT_STEP = 5

type BadgeColour = Literal["green", "orange", "gray"]


@dataclass(frozen=True, kw_only=True)
class TotalBadge:
    """A split's total in words, and how the badge showing it looks."""

    text: str
    colour: BadgeColour
    icon: str


def percent_label(holding: HoldingId) -> str:
    """Label a holding's percentage box, such as "% in VWRP (modelled)"."""
    return f"% in {holding_name(holding)}"


def total_badge(slot: Slot) -> TotalBadge:
    """Say what a split adds up to and, if it is not 100, what to change."""
    if not slot.included:
        return TotalBadge(text="Left out", colour="gray", icon=":material/visibility_off:")
    total = slot.split.total
    if total == WHOLE:
        return TotalBadge(text="Adds up to 100%", colour="green", icon=":material/check:")
    change = f"take {total - WHOLE} off" if total > WHOLE else f"add {WHOLE - total} more"
    return TotalBadge(
        text=f"Adds up to {total}%: {change}", colour="orange", icon=":material/edit:"
    )


def next_blocker(slots: Sequence[Slot]) -> str | None:
    """Say why the splits cannot be stress-tested yet, or return ``None`` if they can."""
    if not any(slot.included for slot in slots):
        return NOTHING_INCLUDED
    names = display_names(slots)
    unfinished = [
        f"{markdown_text(name)} adds up to {slot.split.total}%, not 100%."
        for slot, name in zip(slots, names, strict=True)
        if slot.included and not slot.split.is_complete
    ]
    return " ".join(unfinished) or None


@dataclass(frozen=True, kw_only=True)
class CompositionPoint:
    """How much of one split is in one holding, for the chart."""

    split: str
    holding: str
    kind: str
    percent: int
    order: int


@dataclass(frozen=True, kw_only=True)
class CompositionView:
    """The chart of what each included split holds, one bar per split."""

    points: tuple[CompositionPoint, ...]
    splits: tuple[str, ...]
    x_max: int = WHOLE
    """The axis always reaches 100, so a split that adds up to less shows its gap."""
    kinds: tuple[str, ...] = tuple(KIND_LABELS[kind] for kind in AssetKind)
    x_title: str = COMPOSITION_X_TITLE
    split_title: str = COMPOSITION_SPLIT
    holding_title: str = COMPOSITION_HOLDING
    kind_title: str = COMPOSITION_KIND
    percent_title: str = COMPOSITION_PERCENT


def composition_view(slots: Sequence[Slot]) -> CompositionView:
    """Show what each included split holds: shares first, then bonds, then cash."""
    shown = [
        (name, slot.split)
        for slot, name in zip(slots, display_names(slots), strict=True)
        if slot.included
    ]
    points = tuple(
        CompositionPoint(
            split=name, holding=holding_name(holding), kind=kind, percent=percent, order=order
        )
        for name, split in shown
        for order, (holding, kind, percent) in enumerate(_by_kind(split))
    )
    largest = max((split.total for _, split in shown), default=WHOLE)
    return CompositionView(
        points=points, splits=tuple(name for name, _ in shown), x_max=max(WHOLE, largest)
    )


def _by_kind(split: Split) -> list[tuple[HoldingId, str, int]]:
    """A split's holdings with their kinds, shares first, leaving out any at 0%."""
    kinds = list(CompositionView.kinds)
    held = [
        (holding, holding_kind(holding), percent)
        for holding, percent in split.percentages.items()
        if percent
    ]
    return sorted(held, key=lambda item: kinds.index(item[1]))
