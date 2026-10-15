"""Splits of money between the building blocks, the four places that hold them, and the examples.

A split's percentages are whole numbers, so "adds up to 100" is exact. The examples are there to
show the tool working; they are not advice.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from crashmodel.data.blocks import Block

WHOLE = 100


@dataclass(frozen=True, kw_only=True)
class Split:
    """A named split of money between building blocks.

    Attributes:
        name: What the visitor calls it.
        percentages: Whole percentages by block. Blocks not listed hold nothing.
    """

    name: str
    percentages: Mapping[Block, int]

    def __post_init__(self) -> None:
        """Keep a read-only copy of the percentages, so a split never changes once made."""
        object.__setattr__(self, "percentages", MappingProxyType(dict(self.percentages)))

    @property
    def total(self) -> int:
        """The percentages added up."""
        return sum(self.percentages.values())

    @property
    def is_complete(self) -> bool:
        """Whether the percentages add up to exactly 100."""
        return self.total == WHOLE

    def weights(self) -> dict[Block, float]:
        """Each held block's share as a fraction, for the engine."""
        return {block: percent / WHOLE for block, percent in self.percentages.items() if percent}


CAUTIOUS = Split(
    name="Cautious", percentages={Block.GLOBAL_SHARES: 20, Block.UK_BONDS: 60, Block.CASH: 20}
)
BALANCED = Split(name="Balanced", percentages={Block.GLOBAL_SHARES: 60, Block.UK_BONDS: 40})
ADVENTUROUS = Split(name="Adventurous", percentages={Block.GLOBAL_SHARES: 100})
CASH_ONLY = Split(name="Cash only", percentages={Block.CASH: 100})

EXAMPLE_SPLITS = (CAUTIOUS, BALANCED, ADVENTUROUS, CASH_ONLY)
"""The example journey every visitor starts with. Its position also fixes each split's colour."""

SLOT_COUNT = 4
"""Up to four splits are compared at once."""


@dataclass(frozen=True, kw_only=True)
class Slot:
    """One of the four places for a split. Its position fixes the split's colour on charts.

    Attributes:
        split: The split it holds.
        included: Whether the split takes part in the comparison.
    """

    split: Split
    included: bool = True


def example_slots() -> tuple[Slot, ...]:
    """Return the examples in the four places."""
    return tuple(Slot(split=split) for split in EXAMPLE_SPLITS)


def empty_slots() -> tuple[Slot, ...]:
    """Return four empty places, named Split 1 to Split 4, with only the first included."""
    return tuple(
        Slot(split=Split(name=f"Split {number}", percentages={}), included=number == 1)
        for number in range(1, SLOT_COUNT + 1)
    )
