"""Share market returns from the Kenneth R. French Data Library, fetched when the app runs.

The library is free to download but grants no licence to redistribute, and is built from
proprietary sources. So its data is fetched at runtime, held in memory, never written to disk and
never committed (ADR 0002). Each file is a zipped CSV of monthly factor returns in percent, and the
market's total return in US dollars is ``Mkt-RF`` plus ``RF``.

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

HEADER = ("", "Mkt-RF", "SMB", "HML", "RF")
PERCENT = 100.0
MARKET_LIMIT = 60.0
"""Largest plausible monthly market move in percent; some 1930s US months exceed 30."""
RISK_FREE_RANGE = (-1.0, 3.0)
"""Plausible monthly one-month Treasury bill returns in percent, which have dipped below zero."""
MISSING_DATA = (-99.99, -999.0)
MINIMUM_MONTHS = 12
MAX_DOWNLOAD_BYTES = 1_000_000
"""The zips are tens of kilobytes; anything far larger is not the expected file."""
MAX_CSV_BYTES = 5_000_000
BYTE_ORDER_MARK = "\ufeff"
"""Some editors start a text file with this invisible character."""

_UNREADABLE_ZIP = (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError, RuntimeError)
"""What the zipfile module raises for a damaged, cut short, encrypted or unsupported archive."""

_VINTAGE = re.compile(r"\busing the (\d{4})(\d{2}) (\w+) database\b", re.ASCII)
_MONTH_KEY = re.compile(r"(\d{4})(\d{2})", re.ASCII)
_NUMBER = re.compile(r"-?\d+(\.\d+)?", re.ASCII)


class SourceUnavailableError(Exception):
    """The share data could not be fetched or read, so it is not shown."""


@dataclass(frozen=True, kw_only=True)
class FrenchFile:
    """One of the library's files: which market it covers, and where it is."""

    market: str
    url: str


US_MARKET = FrenchFile(market="US", url=f"{_FILES_URL}F-F_Research_Data_Factors_CSV.zip")
DEVELOPED_MARKETS = FrenchFile(
    market="Developed markets", url=f"{_FILES_URL}Developed_3_Factors_CSV.zip"
)


@dataclass(frozen=True, kw_only=True)
class Vintage:
    """Which monthly update of the library a file comes from, and its underlying database."""

    month: Month
    database: str


@dataclass(frozen=True, kw_only=True)
class MarketReturns:
    """A market's monthly total returns in US dollars, as decimals, and their vintage."""

    returns: MonthlySeries
    vintage: Vintage


def fetch_market_returns(client: httpx.Client, file: FrenchFile) -> MarketReturns:
    """Download and read one of the library's files.

    Raises:
        SourceUnavailableError: If the download fails or the file is not as expected.
    """
    content = _download(client, file.url, file.market)
    try:
        return parse_market_returns(read_zipped_csv(content))
    except ValueError as error:
        raise SourceUnavailableError(f"{file.market}: the file was not as expected") from error


def _download(client: httpx.Client, url: str, label: str) -> bytes:
    try:
        response = client.get(url)
    except httpx.HTTPError as error:
        raise SourceUnavailableError(f"{label}: the download failed") from error
    if not response.is_success:
        raise SourceUnavailableError(f"{label}: the server answered HTTP {response.status_code}")
    return response.content


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


def parse_market_returns(text: str) -> MarketReturns:
    """Read the monthly section of a library CSV into market total returns.

    The monthly section starts at the first header line and ends at the first blank line; the
    annual section after it is ignored.

    Raises:
        ValueError: If the vintage, header or rows are not as expected, or a value is missing or
            implausible.
    """
    lines = text.removeprefix(BYTE_ORDER_MARK).splitlines()
    vintage = _VINTAGE.search(lines[0]) if lines else None
    if vintage is None:
        raise ValueError("the first line does not give the data vintage")
    start = next((index for index, line in enumerate(lines) if _fields(line) == HEADER), None)
    if start is None:
        raise ValueError("the monthly header is missing or has changed")
    pairs: list[tuple[Month, float]] = []
    for line in lines[start + 1 :]:
        if not line.strip():
            break
        pairs.append(_monthly_row(line))
    else:
        raise ValueError("the monthly section does not end, so the file may be cut short")
    if len(pairs) < MINIMUM_MONTHS:
        raise ValueError("too few monthly rows")
    if all(abs(value) < 1 / PERCENT for _, value in pairs):
        raise ValueError("the returns look like decimals, not percent")
    return MarketReturns(
        returns=MonthlySeries.from_pairs(pairs),
        vintage=Vintage(month=Month(int(vintage[1]), int(vintage[2])), database=vintage[3]),
    )


def _fields(line: str) -> tuple[str, ...]:
    return tuple(field.strip() for field in line.split(","))


def _monthly_row(line: str) -> tuple[Month, float]:
    fields = _fields(line)
    if len(fields) != len(HEADER):
        raise ValueError("a row has the wrong number of fields")
    key = _MONTH_KEY.fullmatch(fields[0])
    if key is None:
        raise ValueError("a row does not start with a YYYYMM month")
    market, _, _, risk_free = (_number(field) for field in fields[1:])
    for value in (market, risk_free):
        if any(math.isclose(value, missing) for missing in MISSING_DATA):
            raise ValueError("a month is marked as missing data")
    if not abs(market) < MARKET_LIMIT:
        raise ValueError("a market return is outside the plausible range")
    if not RISK_FREE_RANGE[0] <= risk_free <= RISK_FREE_RANGE[1]:
        raise ValueError("a risk-free return is outside the plausible range")
    return Month(int(key[1]), int(key[2])), (market + risk_free) / PERCENT


def _number(field: str) -> float:
    if not _NUMBER.fullmatch(field):
        raise ValueError("a value is not a plain number")
    return float(field)


FIRMS_SECTION = "Number of Firms in Portfolios"
SIZE_SECTION = "Average Firm Size"
RETURN_RANGE = (-100.0, 300.0)
"""Plausible monthly portfolio returns in percent: nothing loses more than everything, and the
ceiling only catches a garbled value."""

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
    name="Developed markets shares by size",
    url=f"{_FILES_URL}Developed_6_Portfolios_ME_BE-ME_CSV.zip",
    returns_section="Average Value Weighted Returns -- Monthly",
    portfolios=BIG + SMALL,
)
EMERGING_BY_SIZE = PortfolioFile(
    name="Emerging markets shares by size",
    url=f"{_FILES_URL}Emerging_Markets_6_Portfolios_ME_BE-ME_CSV.zip",
    returns_section="Average Value Weighted Returns -- Monthly",
    portfolios=BIG + SMALL,
)
PORTFOLIO_FILES = (US_BY_SIZE, DEVELOPED_BY_SIZE, EMERGING_BY_SIZE)


@dataclass(frozen=True, kw_only=True)
class Portfolios:
    """A file's portfolios in US dollars, by column name, and the file's vintage."""

    portfolios: Mapping[str, SizedPortfolio]
    vintage: Vintage


def fetch_portfolios(client: httpx.Client, file: PortfolioFile) -> Portfolios:
    """Download and read one of the library's size portfolio files.

    Raises:
        SourceUnavailableError: If the download fails or the file is not as expected.
    """
    content = _download(client, file.url, file.name)
    try:
        return parse_portfolios(read_zipped_csv(content), file)
    except ValueError as error:
        raise SourceUnavailableError(f"{file.name}: the file was not as expected") from error


def parse_portfolios(text: str, file: PortfolioFile) -> Portfolios:
    """Read a size portfolio file's monthly returns, firm counts and firm sizes.

    Each section starts with its title, then a header line, and ends at the first blank line. Only
    the file's named columns are read, so a value missing from a column the app does not use does
    not matter. A portfolio may start with missing months, which are left out; a month missing after
    that makes the file unusable.

    Raises:
        ValueError: If the vintage, a section or a column is missing, or a value is missing or
            implausible.
    """
    lines = text.removeprefix(BYTE_ORDER_MARK).splitlines()
    vintage = _VINTAGE.search(lines[0]) if lines else None
    if vintage is None:
        raise ValueError("the first line does not give the data vintage")
    returns = _section(lines, file.returns_section, file.portfolios)
    firms = _section(lines, FIRMS_SECTION, file.portfolios)
    sizes = _section(lines, SIZE_SECTION, file.portfolios)
    if not returns.keys() == firms.keys() == sizes.keys():
        raise ValueError("the sections cover different months")
    percents = [value for row in returns.values() for value in row if value is not None]
    if percents and all(abs(value) < 1 / PERCENT for value in percents):
        raise ValueError("the returns look like decimals, not percent")
    rows = [(month, returns[month], firms[month], sizes[month]) for month in returns]
    return Portfolios(
        portfolios={
            name: _portfolio([(month, r[i], n[i], s[i]) for month, r, n, s in rows])
            for i, name in enumerate(file.portfolios)
        },
        vintage=Vintage(month=Month(int(vintage[1]), int(vintage[2])), database=vintage[3]),
    )


def _section(
    lines: list[str], title: str, columns: tuple[str, ...]
) -> dict[Month, tuple[float | None, ...]]:
    start = next((index for index, line in enumerate(lines) if line.strip() == title), None)
    if start is None or start + 1 >= len(lines):
        raise ValueError(f"the section {title!r} is missing")
    header = _fields(lines[start + 1])
    if header[:1] != ("",) or not set(columns) <= set(header):
        raise ValueError(f"the section {title!r} lacks a column the app uses")
    positions = [header.index(column) for column in columns]
    rows: dict[Month, tuple[float | None, ...]] = {}
    for line in lines[start + 2 :]:
        if not line.strip():
            break
        fields = _fields(line)
        if len(fields) != len(header):
            raise ValueError("a row has the wrong number of fields")
        key = _MONTH_KEY.fullmatch(fields[0])
        if key is None:
            raise ValueError("a row does not start with a YYYYMM month")
        rows[Month(int(key[1]), int(key[2]))] = tuple(_value(fields[i]) for i in positions)
    else:
        raise ValueError(f"the section {title!r} does not end, so the file may be cut short")
    if len(rows) < MINIMUM_MONTHS:
        raise ValueError(f"the section {title!r} has too few monthly rows")
    return rows


def _value(field: str) -> float | None:
    value = _number(field)
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
