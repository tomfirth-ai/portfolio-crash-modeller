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
from dataclasses import dataclass

import httpx

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
FRENCH_FILES = (US_MARKET, DEVELOPED_MARKETS)


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
    try:
        response = client.get(file.url)
    except httpx.HTTPError as error:
        raise SourceUnavailableError(f"{file.market}: the download failed") from error
    if not response.is_success:
        raise SourceUnavailableError(
            f"{file.market}: the server answered HTTP {response.status_code}"
        )
    try:
        return parse_market_returns(read_zipped_csv(response.content))
    except ValueError as error:
        raise SourceUnavailableError(f"{file.market}: the file was not as expected") from error


def read_zipped_csv(content: bytes) -> str:
    """Return the text of the single CSV file inside a zip, without touching the disk.

    Raises:
        ValueError: If the content is too large, not a zip, has other than one CSV file, or is
            not plain ASCII text.
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
    except zipfile.BadZipFile as error:
        raise ValueError("the download is not a zip file") from error
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
    lines = text.lstrip("﻿").splitlines()
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
