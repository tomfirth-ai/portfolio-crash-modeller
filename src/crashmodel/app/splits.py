"""Splits of money between the building blocks, and the illustrative examples.

A split's percentages are whole numbers, so "adds up to 100" is exact. The examples are there to
show the tool working; they are not advice.
"""

from collections.abc import Mapping
from dataclasses import dataclass

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
