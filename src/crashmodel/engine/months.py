"""Calendar months, and series of monthly values with no gaps.

Monthly data from different publishers is labelled by different month-end dates: a trading day, a
calendar day, or just the month. Keying everything by calendar month lines the sources up, and a
series that cannot have gaps means a missing month can never be mistaken for a zero return.
"""

import calendar
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date
from typing import Self

MONTHS_IN_YEAR = 12

_MONTH_TEXT = re.compile(r"(\d{4})-(\d{2})")


@dataclass(frozen=True, order=True)
class Month:
    """A calendar month, such as June 2007.

    Adding a whole number moves forward that many months, and subtracting one month from another
    gives the number of months between them.
    """

    year: int
    month: int

    def __post_init__(self) -> None:
        """Reject month numbers outside 1 to 12."""
        if not 1 <= self.month <= MONTHS_IN_YEAR:
            raise ValueError(f"month must be from 1 to 12, not {self.month}")

    @classmethod
    def parse(cls, text: str) -> Self:
        """Read a month written as ``YYYY-MM``."""
        match = _MONTH_TEXT.fullmatch(text)
        if match is None:
            raise ValueError(f"expected a month written as YYYY-MM, not {text!r}")
        return cls(int(match[1]), int(match[2]))

    @classmethod
    def of(cls, day: date) -> Self:
        """Return the month a date falls in."""
        return cls(day.year, day.month)

    def __str__(self) -> str:
        """Write the month as ``YYYY-MM``."""
        return f"{self.year:04d}-{self.month:02d}"

    def __add__(self, months: int) -> "Month":
        """Return the month that many months later, or earlier if negative."""
        index = self._index() + months
        return Month(index // MONTHS_IN_YEAR, index % MONTHS_IN_YEAR + 1)

    def __sub__(self, other: "Month") -> int:
        """Return how many months ``other`` is before this month."""
        return self._index() - other._index()

    @property
    def previous(self) -> "Month":
        """The month before."""
        return self + -1

    @property
    def days(self) -> int:
        """The number of calendar days in the month."""
        return calendar.monthrange(self.year, self.month)[1]

    @property
    def first_day(self) -> date:
        """The month's first calendar day."""
        return date(self.year, self.month, 1)

    @property
    def last_day(self) -> date:
        """The month's last calendar day."""
        return date(self.year, self.month, self.days)

    def _index(self) -> int:
        return self.year * MONTHS_IN_YEAR + self.month - 1


def month_range(first: Month, last: Month) -> Iterator[Month]:
    """Yield every month from ``first`` to ``last``, both included."""
    for offset in range(last - first + 1):
        yield first + offset


@dataclass(frozen=True)
class MonthlySeries:
    """One value for each of a run of consecutive months, with no gaps.

    Attributes:
        start: The first month.
        values: The values, one per month from ``start`` on.
    """

    start: Month
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        """Reject an empty series, which has no months to describe."""
        if not self.values:
            raise ValueError("a monthly series needs at least one value")

    @classmethod
    def from_pairs(cls, pairs: Iterable[tuple[Month, float]]) -> Self:
        """Build a series from ``(month, value)`` pairs that run month by month with no gaps.

        Raises:
            ValueError: If the pairs are empty, out of order, repeated or have a gap.
        """
        months: list[Month] = []
        values: list[float] = []
        for month, value in pairs:
            if months and month != months[-1] + 1:
                raise ValueError(f"{month} does not follow {months[-1]}: series must have no gaps")
            months.append(month)
            values.append(value)
        if not months:
            raise ValueError("a monthly series needs at least one value")
        return cls(months[0], tuple(values))

    @property
    def end(self) -> Month:
        """The last month."""
        return self.start + (len(self.values) - 1)

    def __len__(self) -> int:
        """Return the number of months."""
        return len(self.values)

    def __getitem__(self, month: Month) -> float:
        """Return the value for a month.

        Raises:
            KeyError: If the month is outside the series.
        """
        offset = month - self.start
        if not 0 <= offset < len(self.values):
            raise KeyError(f"{month} is outside {self.start} to {self.end}")
        return self.values[offset]

    def items(self) -> Iterator[tuple[Month, float]]:
        """Yield ``(month, value)`` pairs in order."""
        for offset, value in enumerate(self.values):
            yield self.start + offset, value

    def covers(self, first: Month, last: Month) -> bool:
        """Whether the series has a value for every month from ``first`` to ``last``."""
        return self.start <= first and last <= self.end

    def between(self, first: Month, last: Month) -> "MonthlySeries":
        """Return the part of the series from ``first`` to ``last``, both included.

        Raises:
            KeyError: If the series does not cover the whole range.
        """
        if not self.covers(first, last):
            raise KeyError(f"{first} to {last} is not inside {self.start} to {self.end}")
        offset = first - self.start
        return MonthlySeries(first, self.values[offset : offset + (last - first) + 1])
