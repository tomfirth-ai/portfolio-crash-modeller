"""What the Design page says: what each box means, each split's total, and what is still needed."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from crashmodel.app.journey import DESIGN
from crashmodel.app.presenters.blocks import BLOCK_LABELS
from crashmodel.app.presenters.names import markdown_text
from crashmodel.app.splits import EXAMPLE_SPLITS, WHOLE, Slot, display_names
from crashmodel.data.blocks import Block

TITLE = DESIGN.title
INTRODUCTION = (
    "Split £100 between the building blocks, in whole percentages that add up to 100. You can "
    "compare up to four splits; switch one off to leave it out."
)
START_OWN = "Start your own"
SHOW_EXAMPLES = "Back to the examples"
INCLUDE = "Include"
NAME = "Name"
TEMPLATE = "Fill from an example"
TEMPLATE_PLACEHOLDER = "Choose an example"
TEMPLATE_NAMES = tuple(split.name for split in EXAMPLE_SPLITS)
COMPOSITION_HEADING = "What each split holds"
COMPOSITION_X_TITLE = "Share of £100 (%)"
COMPOSITION_SPLIT = "Split"
COMPOSITION_BLOCK = "Building block"
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


def block_label(block: Block) -> str:
    """Label a block's percentage box, such as "Cash (%)"."""
    return f"{BLOCK_LABELS[block]} (%)"


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
    """How much of one split is in one block, for the chart."""

    split: str
    block: str
    percent: int
    order: int


@dataclass(frozen=True, kw_only=True)
class CompositionView:
    """The chart of what each included split holds, one bar per split."""

    points: tuple[CompositionPoint, ...]
    splits: tuple[str, ...]
    x_max: int = WHOLE
    """The axis always reaches 100, so a split that adds up to less shows its gap."""
    blocks: tuple[str, ...] = tuple(BLOCK_LABELS[block] for block in Block)
    x_title: str = COMPOSITION_X_TITLE
    split_title: str = COMPOSITION_SPLIT
    block_title: str = COMPOSITION_BLOCK
    percent_title: str = COMPOSITION_PERCENT


def composition_view(slots: Sequence[Slot]) -> CompositionView:
    """Show what each included split holds, block by block, in the blocks' usual order."""
    shown = [
        (name, slot.split)
        for slot, name in zip(slots, display_names(slots), strict=True)
        if slot.included
    ]
    points = tuple(
        CompositionPoint(split=name, block=BLOCK_LABELS[block], percent=percent, order=order)
        for name, split in shown
        for order, block in enumerate(Block)
        if (percent := split.percentages.get(block, 0))
    )
    largest = max((split.total for _, split in shown), default=WHOLE)
    return CompositionView(
        points=points, splits=tuple(name for name, _ in shown), x_max=max(WHOLE, largest)
    )
