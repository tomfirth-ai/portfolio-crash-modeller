"""The building blocks a split is made from.

Each block is a kind of investment with one monthly return series in pounds. What each is called
and how it is explained to a visitor lives with the app's presenters; this module only names them.
"""

from enum import StrEnum


class Block(StrEnum):
    """A building block of a split."""

    GLOBAL_SHARES = "global_shares"
    US_SHARES = "us_shares"
    UK_BONDS = "uk_bonds"
    CASH = "cash"


SHARE_BLOCKS = frozenset({Block.GLOBAL_SHARES, Block.US_SHARES})
"""Blocks whose data is fetched when the app runs, and so may be unavailable."""
