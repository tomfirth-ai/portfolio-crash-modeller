"""Share portfolios from the Kenneth R. French Data Library, fetched when the app runs.

The library is free to download but grants no licence to redistribute, and is built from
proprietary sources. So its data is fetched at runtime, held in memory, never written to disk and
never committed (ADR 0002). The app reads three of its files, which group companies by size: US
companies in tenths by market value, and developed and emerging markets companies split into big
and small. Each file is a zipped CSV with sections of monthly figures: the value-weighted return of
each portfolio in percent, in US dollars and with dividends reinvested; how many firms it held; and
their average market value.

The files are rebuilt every month and their layout could change, so anything unexpected, from a
failed download to an implausible value, makes the source unavailable rather than wrong.
"""

import io
import math
import re
import zipfile
import zlib
from collections.abc import Mapping
from dataclasses import dataclass

import httpx

from crashmodel.engine.indexes import SizedPortfolio
from crashmodel.engine.months import Month, MonthlySeries

LIBRARY_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html"
_FILES_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"

PERCENT = 100.0
RETURN_RANGE = (-100.0, 300.0)
"""Plausible monthly portfolio returns in percent: nothing loses more than everything, and the
ceiling only catches a garbled value."""
MISSING_DATA = (-99.99, -999.0)
MINIMUM_MONTHS = 12
LARGEST_DECIMAL_RETURN = 1.0
"""Over a year or more, some month's return in percent passes 1, while returns written as
decimals, such as 0.03 for 3%, never do."""
MAX_DOWNLOAD_BYTES = 1_000_000
"""The zips are at most a few hundred kilobytes; anything far larger is not the expected file."""
MAX_CSV_BYTES = 5_000_000
BYTE_ORDER_MARK = "﻿"
"""Some editors start a text file with this invisible character."""

FIRMS_SECTION = "Number of Firms in Portfolios"
SIZE_SECTION = "Average Firm Size"

US_SIZE_DECILES = (
    "Hi 10",
    "9-Dec",
    "8-Dec",
    "7-Dec",
    "6-Dec",
    "5-Dec",
    "4-Dec",
    "3-Dec",
    "2-Dec",
    "Lo 10",
)
"""US companies in tenths by market value, largest first."""
BIG = ("BIG LoBM", "ME2 BM2", "BIG HiBM")
"""Companies in the top 90% of market value, split three ways by book-to-market."""
SMALL = ("SMALL LoBM", "ME1 BM2", "SMALL HiBM")
"""Companies in the bottom 10% of market value, split the same way."""

_UNREADABLE_ZIP = (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError, RuntimeError)
"""What the zipfile module raises for a damaged, cut short, encrypted or unsupported archive."""

_VINTAGE = re.compile(r"\busing the (\d{4})(\d{2}) (\w+) database\b", re.ASCII)
_MONTH_KEY = re.compile(r"(\d{4})(\d{2})", re.ASCII)
_NUMBER = re.compile(r"-?\d+(\.\d+)?", re.ASCII)

type _Row = tuple[float | None, ...]


class SourceUnavailableError(Exception):
    """The share data could not be fetched or read, so it is not shown."""


class SourceUnreachableError(SourceUnavailableError):
    """The library's server could not be reached at all, so none of its files can be fetched."""


@dataclass(frozen=True, kw_only=True)
class PortfolioFile:
    """One of the library's files of portfolios of companies grouped by size.

    Attributes:
        name: What it covers, for messages and the Data sources page.
        url: Where it is.
        returns_section: The title of its value-weighted monthly returns, which differs between
            files.
        portfolios: The columns the app uses.
    """

    name: str
    url: str
    returns_section: str
    portfolios: tuple[str, ...]


US_BY_SIZE = PortfolioFile(
    name="US shares by size",
    url=f"{_FILES_URL}Portfolios_Formed_on_ME_CSV.zip",
    returns_section="Average Value Weight Returns -- Monthly",
    portfolios=US_SIZE_DECILES,
)
DEVELOPED_BY_SIZE = PortfolioFile(
    name="developed markets shares by size",
    url=f"{_FILES_URL}Developed_6_Portfolios_ME_BE-ME_CSV.zip",
    returns_section="Average Value Weighted Returns -- Monthly",
    portfolios=BIG + SMALL,
)
EMERGING_BY_SIZE = PortfolioFile(
    name="emerging markets shares by size",
    url=f"{_FILES_URL}Emerging_Markets_6_Portfolios_ME_BE-ME_CSV.zip",
    returns_section="Average Value Weighted Returns -- Monthly",
    portfolios=BIG + SMALL,
)
PORTFOLIO_FILES = (US_BY_SIZE, DEVELOPED_BY_SIZE, EMERGING_BY_SIZE)


@dataclass(frozen=True, kw_only=True)
class Vintage:
    """Which monthly update of the library a file comes from, and its underlying database."""

    month: Month
    database: str


@dataclass(frozen=True, kw_only=True)
class Portfolios:
    """A file's portfolios in US dollars, by column name, and the file's vintage."""

    portfolios: Mapping[str, SizedPortfolio]
    vintage: Vintage


def fetch_portfolios(client: httpx.Client, file: PortfolioFile) -> Portfolios:
    """Download and read one of the library's size portfolio files.

    Raises:
        SourceUnreachableError: If the server cannot be reached, or does not answer in time.
        SourceUnavailableError: If the download fails in another way, or the file is not as
            expected.
    """
    try:
        response = client.get(file.url)
    except httpx.TransportError as error:
        raise SourceUnreachableError(f"{file.name}: the server could not be reached") from error
    except httpx.HTTPError as error:
        raise SourceUnavailableError(f"{file.name}: the download failed") from error
    if not response.is_success:
        raise SourceUnavailableError(
            f"{file.name}: the server answered HTTP {response.status_code}"
        )
    try:
        return parse_portfolios(read_zipped_csv(response.content), file)
    except ValueError as error:
        raise SourceUnavailableError(f"{file.name}: the file was not as expected") from error


def read_zipped_csv(content: bytes) -> str:
    """Return the text of the single CSV file inside a zip, without touching the disk.

    Raises:
        ValueError: If the content is too large, not a readable zip, has other than one CSV file,
            or is not plain ASCII text.
    """
    if len(content) > MAX_DOWNLOAD_BYTES:
        raise ValueError("the download is too large")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = [
                info for info in archive.infolist() if info.filename.lower().endswith(".csv")
            ]
            if len(members) != 1:
                raise ValueError("expected exactly one CSV file in the zip")
            if members[0].file_size > MAX_CSV_BYTES:
                raise ValueError("the CSV file is too large")
            raw = archive.read(members[0])
    except _UNREADABLE_ZIP as error:
        raise ValueError("the download is not a readable zip file") from error
    try:
        return raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("the CSV file is not plain text") from error


def parse_portfolios(text: str, file: PortfolioFile) -> Portfolios:
    """Read a size portfolio file's monthly returns, firm counts and firm sizes.

    Each section starts with its title, then a header line, and ends at the first blank line or
    with the file. Every section must cover the same months, so a file cut short shows up as a
    section with fewer. Only the file's named columns are read, so a value missing from a column the
    app does not use does not matter. A portfolio may start with missing months, which are left out;
    a month missing after that makes the file unusable.

    Raises:
        ValueError: If the vintage, a section or a column is missing, the months repeat or have a
            gap, or a value is missing or implausible.
    """
    lines = text.removeprefix(BYTE_ORDER_MARK).splitlines()
    vintage = _VINTAGE.search(lines[0]) if lines else None
    if vintage is None:
        raise ValueError("the first line does not give the data vintage")
    returns = _section(lines, file.returns_section, file.portfolios)
    firms = _section(lines, FIRMS_SECTION, file.portfolios)
    sizes = _section(lines, SIZE_SECTION, file.portfolios)
    months = [month for month, _ in returns]
    if [month for month, _ in firms] != months or [month for month, _ in sizes] != months:
        raise ValueError("the sections cover different months")
    percents = [value for _, row in returns for value in row if value is not None]
    if percents and all(abs(value) < LARGEST_DECIMAL_RETURN for value in percents):
        raise ValueError("the returns look like decimals, not percent")
    return Portfolios(
        portfolios={
            name: _portfolio(
                [
                    (month, r[column], n[column], s[column])
                    for month, (_, r), (_, n), (_, s) in zip(
                        months, returns, firms, sizes, strict=True
                    )
                ]
            )
            for column, name in enumerate(file.portfolios)
        },
        vintage=Vintage(month=Month(int(vintage[1]), int(vintage[2])), database=vintage[3]),
    )


def _section(lines: list[str], title: str, columns: tuple[str, ...]) -> list[tuple[Month, _Row]]:
    start = next((index for index, line in enumerate(lines) if line.strip() == title), None)
    if start is None or start + 1 >= len(lines):
        raise ValueError(f"the section {title!r} is missing")
    header = _fields(lines[start + 1])
    if header[:1] != ("",) or not set(columns) <= set(header):
        raise ValueError(f"the section {title!r} lacks a column the app uses")
    positions = [header.index(column) for column in columns]
    rows: list[tuple[Month, _Row]] = []
    for line in lines[start + 2 :]:
        if not line.strip():
            break
        fields = _fields(line)
        if len(fields) != len(header):
            raise ValueError("a row has the wrong number of fields")
        key = _MONTH_KEY.fullmatch(fields[0])
        if key is None:
            raise ValueError("a row does not start with a YYYYMM month")
        rows.append((Month(int(key[1]), int(key[2])), tuple(_value(fields[i]) for i in positions)))
    if len(rows) < MINIMUM_MONTHS:
        raise ValueError(f"the section {title!r} has too few monthly rows")
    return rows


def _fields(line: str) -> tuple[str, ...]:
    return tuple(field.strip() for field in line.split(","))


def _value(field: str) -> float | None:
    if not _NUMBER.fullmatch(field):
        raise ValueError("a value is not a plain number")
    value = float(field)
    return None if any(math.isclose(value, missing) for missing in MISSING_DATA) else value


def _portfolio(
    rows: list[tuple[Month, float | None, float | None, float | None]],
) -> SizedPortfolio:
    first = next((i for i, (_, *values) in enumerate(rows) if None not in values), None)
    if first is None:
        raise ValueError("a portfolio has no complete month")
    kept: list[tuple[Month, float, float, float]] = []
    for month, percent, count, size in rows[first:]:
        if percent is None or count is None or size is None:
            raise ValueError("a month is marked as missing data")
        if not RETURN_RANGE[0] < percent < RETURN_RANGE[1]:
            raise ValueError("a return is outside the plausible range")
        if not count.is_integer():
            raise ValueError("a firm count is not a whole number")
        kept.append((month, percent / PERCENT, count, size))
    return SizedPortfolio(
        returns=MonthlySeries.from_pairs((month, r) for month, r, _, _ in kept),
        firms=MonthlySeries.from_pairs((month, n) for month, _, n, _ in kept),
        average_size=MonthlySeries.from_pairs((month, s) for month, _, _, s in kept),
    )
