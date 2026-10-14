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
"""Line 2 is a name, 3 a ticker, 4 an amount, 5 a unit count with decimals and 6 a date."""

GitRunner = Callable[..., str]
"""Runs git in the test repository and returns its standard output."""
