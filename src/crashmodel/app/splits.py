"""Splits of money between funds and indexes, the places that hold them, and the examples.

A split's percentages are whole numbers, so "adds up to 100" is exact. The examples hold indexes,
never named funds, and are there to show the tool working; they are not advice.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType

from crashmodel.data.catalogue import HoldingId

WHOLE = 100


@dataclass(frozen=True, kw_only=True)
class Split:
    """A named split of money between funds and indexes.

    Attributes:
        name: What the visitor calls it.
        percentages: Whole percentages by holding, in the order the visitor chose them. A holding
            may be at 0% while the visitor works out the split.
    """

    name: str
    percentages: Mapping[HoldingId, int]

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

    def weights(self) -> dict[HoldingId, float]:
        """Each holding's share as a fraction, for the engine, leaving out any at 0%."""
        return {
            holding: percent / WHOLE for holding, percent in self.percentages.items() if percent
        }


MOSTLY_BONDS = Split(
    name="Mostly bonds",
    percentages={"ftse_all_world": 20, "ftse_gilts_all_stocks": 60, "sonia": 20},
)
SHARES_AND_BONDS = Split(
    name="Shares and bonds", percentages={"ftse_all_world": 60, "ftse_gilts_all_stocks": 40}
)
ALL_SHARES = Split(name="All shares", percentages={"ftse_all_world": 100})
CASH_ONLY = Split(name="Cash only", percentages={"sonia": 100})

EXAMPLE_SPLITS = (MOSTLY_BONDS, SHARES_AND_BONDS, ALL_SHARES, CASH_ONLY)
"""The example journey every visitor starts with. Its position also fixes each split's colour.

The names say what each split holds, never who it might suit: a name such as "Cautious" is a risk
profile, and would read as advice.
"""

MOST_SLOTS = 6
"""Up to six splits are compared at once: the four examples and two more."""


@dataclass(frozen=True, kw_only=True)
class Slot:
    """One of the places for a split. Its position fixes the split's colour on charts.

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
        replace(empty_slot(number), included=number == 1)
        for number in range(1, len(EXAMPLE_SPLITS) + 1)
    )


def empty_slot(number: int) -> Slot:
    """Return an included place holding nothing yet, named after its number, such as "Split 5"."""
    return Slot(split=Split(name=f"Split {number}", percentages={}))


def display_names(slots: Sequence[Slot]) -> tuple[str, ...]:
    """Return a name for each slot's split, in order, that is never blank.

    A blank name becomes "Split 2" after its place. Among included splits a repeated name gets a
    number, such as "All shares (2)", so that a chart or table never mixes two splits up.
    """
    shown: list[str] = []
    taken: set[str] = set()
    for number, slot in enumerate(slots, start=1):
        name = slot.split.name.strip() or f"Split {number}"
        if slot.included:
            base, copy = name, 1
            while name in taken:
                copy += 1
                name = f"{base} ({copy})"
            taken.add(name)
        shown.append(name)
    return tuple(shown)
