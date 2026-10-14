"""Synthetic test data for the guard tools. None of these values is real."""

from collections.abc import Callable

SENTINEL_DENYLIST = """\
# Synthetic sentinels for tests. None of these is real.

Zebedee Quartermaine
ZQXW
271828
314.159
2031-02-17
"""
NAME_LINE, TICKER_LINE, AMOUNT_LINE, UNITS_LINE, DATE_LINE = 3, 4, 5, 6, 7
"""Where each kind of sentinel sits in ``SENTINEL_DENYLIST``."""

GitRunner = Callable[..., str]
"""Runs git in the test repository and returns its standard output."""
