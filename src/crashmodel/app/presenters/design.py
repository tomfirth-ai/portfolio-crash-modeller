"""What the Design page says: what each box means, each split's total, and what is still needed."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from crashmodel.app.journey import DESIGN
from crashmodel.app.presenters.blocks import BLOCK_LABELS
from crashmodel.app.presenters.names import display_names, markdown_text
from crashmodel.app.splits import EXAMPLE_SPLITS, WHOLE, Slot
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
