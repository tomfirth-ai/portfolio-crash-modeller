"""Synthetic test data for the guard tools. None of these values is real."""

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
