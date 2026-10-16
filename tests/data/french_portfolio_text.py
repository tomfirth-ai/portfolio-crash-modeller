"""Synthetic text in the layout of the French library's size portfolio files, for tests.

Every value is a round number made up here; no real data from the library is used or stored. The
layout copies the real files' structure: CRLF line endings, a preamble, indented section titles, a
header line starting with a comma, padded rows, sections the app does not read, and the footer.
"""

from collections.abc import Callable, Sequence

from crashmodel.data.french import (
    BIG,
    FIRMS_SECTION,
    SIZE_SECTION,
    SMALL,
    US_BY_SIZE,
    US_SIZE_DECILES,
    PortfolioFile,
)
from crashmodel.engine.months import Month

type Cell = tuple[float | None, float | None, float | None]
"""A portfolio's return in percent, number of firms and average firm size; ``None`` is missing."""
type Values = Callable[[str, Month], Cell]

CRLF = "\r\n"
MISSING = "-99.99"
FIRST_MONTH = Month(2007, 1)
WIDTH = 8
US_HEADER = (
    "<= 0",
    "Lo 30",
    "Med 40",
    "Hi 30",
    "Lo 20",
    "Qnt 2",
    "Qnt 3",
    "Qnt 4",
    "Hi 20",
    *reversed(US_SIZE_DECILES),
)
"""Every column of the US file. The first is always missing, as in the real file."""
SIX_HEADER = (*SMALL, *BIG)
CYCLE = (1.0, -2.0, 3.0, -1.0)


def steady(column: str, month: Month) -> Cell:
    """Ten firms of size 100 in every portfolio, with returns that repeat every four months."""
    del column
    return CYCLE[(month.month - 1) % len(CYCLE)], 10, 100


def portfolio_text(
    file: PortfolioFile,
    *,
    start: Month = FIRST_MONTH,
    months: int = 24,
    values: Values = steady,
    header: Sequence[str] | None = None,
) -> str:
    """Return synthetic file text for ``file``, with ``months`` monthly rows from ``start``.

    As in the real files, the US layout pads each value on the left and ends with the copyright
    line, while the developed and emerging layout pads on the right and ends with its last row.
    """
    us = file == US_BY_SIZE
    columns = header if header is not None else US_HEADER if us else SIX_HEADER
    keys = [start + offset for offset in range(months)]
    vintage = f"{keys[-1].year:04d}{keys[-1].month:02d}"

    def section(title: str, field: int, *, number: str = ".2f") -> list[str]:
        rows = []
        for month in keys:
            cells = []
            for column in columns:
                value = None if column == "<= 0" else values(column, month)[field]
                cells.append(MISSING if value is None else f"{value:{number}}")
            padded = [cell.rjust(WIDTH) if us else cell.ljust(WIDTH) for cell in cells]
            rows.append(",".join([f"{month.year:04d}{month.month:02d}", *padded]))
        return ["", "", f"  {title}", ",".join(["", *columns]), *rows]

    lines = [
        f"This file was created using the {vintage} Synthetic database.  It contains",
        "value- and equal-weighted returns for synthetic size portfolios.",
        "",
        "Missing data are indicated by -99.99 or -999.",
        *section(file.returns_section, 0),
        *section("Average Equal Weighted Returns -- Monthly", 0),
        *section("Value Weight Returns -- Annual from January to December", 0)[:4],
        f"{start.year:04d}," + ",".join("1.00".rjust(WIDTH) for _ in columns),
        *section(FIRMS_SECTION, 1, number="g"),
        *section(SIZE_SECTION, 2),
    ]
    if us:
        lines += ["", "Copyright 2026 Eugene F. Fama and Kenneth R. French"]
    return CRLF.join(lines) + CRLF
