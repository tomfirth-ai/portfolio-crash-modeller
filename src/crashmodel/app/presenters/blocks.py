"""What each building block is called, and what it is, in plain words."""

from collections.abc import Iterable

from crashmodel.app.presenters.format import listed
from crashmodel.data.blocks import Block

BLOCK_LABELS = {
    Block.GLOBAL_SHARES: "Global shares",
    Block.US_SHARES: "US shares",
    Block.UK_BONDS: "UK government bonds",
    Block.CASH: "Cash",
}

BLOCK_DEFINITIONS = {
    Block.GLOBAL_SHARES: (
        "Shares in companies across 23 developed countries, including the UK and the US, in "
        "proportion to their size, with dividends reinvested. Emerging markets are not included."
    ),
    Block.US_SHARES: (
        "Shares in US companies, in proportion to their size, with dividends reinvested."
    ),
    Block.UK_BONDS: (
        "A 10-year UK government bond, bought new each month at the going yield. Bonds lose value "
        "when interest rates rise and gain when they fall."
    ),
    Block.CASH: (
        "Cash earning the Bank of England's Bank Rate, which a savings account would usually "
        "pay a little less than."
    ),
}


BLOCK_NAMES_IN_TEXT = {
    Block.GLOBAL_SHARES: "global shares",
    Block.US_SHARES: "US shares",
    Block.UK_BONDS: "UK government bonds",
    Block.CASH: "cash",
}
"""How each block is named inside a sentence."""


def block_list(blocks: Iterable[Block]) -> str:
    """Name blocks in a sentence, such as "global shares and UK government bonds"."""
    return listed([BLOCK_NAMES_IN_TEXT[block] for block in blocks])
