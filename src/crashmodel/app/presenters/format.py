"""How numbers, months and money are written, the same way on every page."""

import calendar
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from crashmodel.engine.months import Month

PERCENT = 100
SMALLEST_SHOWN_PERCENT = Decimal("0.5")
"""Falls below half a percent would round to 0%, so they read "less than 1%" instead."""


def percent(fraction: float) -> str:
    """Write a fraction as a whole percentage, rounding halves away from zero: 0.245 is "25%"."""
    value = Decimal(str(fraction)) * PERCENT
    if 0 < value < SMALLEST_SHOWN_PERCENT:
        return "less than 1%"
    return f"{value.quantize(Decimal(1), rounding=ROUND_HALF_UP)}%"


def listed(items: Sequence[str]) -> str:
    """Join items as in a sentence: "a", "a and b", "a, b and c"."""
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


def months(count: int) -> str:
    """Write a number of months: "1 month", "17 months"."""
    return "1 month" if count == 1 else f"{count} months"


def month_name(month: Month) -> str:
    """Write a month as words: "June 2007"."""
    return f"{calendar.month_name[month.month]} {month.year}"


def pounds_and_pence(value: float) -> str:
    """Write an amount to the penny: "£3.40"."""
    rounded = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"£{rounded:,}"


def pounds(value: float) -> str:
    """Write an amount in whole pounds: "£1,234"."""
    rounded = Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return f"£{rounded:,}"
