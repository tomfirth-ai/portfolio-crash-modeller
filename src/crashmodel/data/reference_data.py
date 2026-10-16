"""The open data stored with the app, and the credit each publisher asks for.

Each series is a small CSV file in the ``reference`` folder beside this module, written by
``tools/build_reference_data.py`` from the publisher's own files. A file has a ``month`` column of
``YYYY-MM`` months and one value column, and a ``SOURCE.md`` beside it records where it came from.
"""

import re
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable

from crashmodel.engine.months import Month, MonthlySeries

_NUMBER = re.compile(r"-?\d+(\.\d+)?", re.ASCII)

OPEN_GOVERNMENT_LICENCE = "Open Government Licence v3.0"
OPEN_GOVERNMENT_LICENCE_URL = (
    "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
)
BANK_OF_ENGLAND_DATABASE = "https://www.bankofengland.co.uk/boeapps/database/"


@dataclass(frozen=True, kw_only=True)
class Credit:
    """Where a series comes from, and how its publisher asks to be credited."""

    publisher: str
    dataset: str
    url: str
    licence: str
    licence_url: str
    attribution: str


@dataclass(frozen=True, kw_only=True)
class ReferenceSeries:
    """A monthly series stored with the app.

    Attributes:
        folder: The folder under ``reference`` that holds it, named after its source.
        name: The file name without ``.csv``, which is also the value column's name.
        description: What the values are, in plain words.
        plausible_range: The lowest and highest values that make sense; anything outside is an
            error in the file.
        decimal_places: How many decimal places the values are written to.
        credit: Where it comes from.
    """

    folder: str
    name: str
    description: str
    plausible_range: tuple[float, float]
    decimal_places: int
    credit: Credit

    @property
    def path(self) -> str:
        """The file's path inside the ``reference`` folder."""
        return f"{self.folder}/{self.name}.csv"

    @property
    def header(self) -> str:
        """The file's header line."""
        return f"month,{self.name}"


USD_PER_GBP = ReferenceSeries(
    folder="fed-h10",
    name="usd_per_gbp",
    description="US dollars per pound at the end of each month",
    plausible_range=(0.5, 5.0),
    decimal_places=4,
    credit=Credit(
        publisher="Board of Governors of the Federal Reserve System",
        dataset="H.10 Foreign Exchange Rates: United Kingdom pound, US dollars per pound",
        url="https://www.federalreserve.gov/releases/h10/",
        licence="Public domain",
        licence_url="https://www.federalreserve.gov/disclaimer.htm",
        attribution="Source: Board of Governors of the Federal Reserve System, H.10 release.",
    ),
)

OPEN_GOVERNMENT_ATTRIBUTION = (
    "Contains public sector information licensed under the Open Government Licence v3.0."
)
SONIA_ATTRIBUTION = (
    "SONIA and/or SONIA Compounded Index data licensed under the Open Government Licence v3.0 and "
    'copyright the Governor and Company of the Bank of England. The trade marks "Bank of England" '
    'and "SONIA" are registered trade marks of the Bank of England.'
)
"""The statement the Bank of England asks for wherever SONIA data is reused."""

YIELD_CURVE_CREDIT = Credit(
    publisher="Bank of England",
    dataset="Yields from British Government Securities: nominal zero-coupon and par yields, end of "
    "month",
    url=BANK_OF_ENGLAND_DATABASE,
    licence=OPEN_GOVERNMENT_LICENCE,
    licence_url=OPEN_GOVERNMENT_LICENCE_URL,
    attribution=OPEN_GOVERNMENT_ATTRIBUTION,
)
STERLING_CASH_CREDIT = Credit(
    publisher="Bank of England",
    dataset="SONIA (Sterling Overnight Index Average) and Official Bank Rate, daily",
    url=BANK_OF_ENGLAND_DATABASE,
    licence=OPEN_GOVERNMENT_LICENCE,
    licence_url=OPEN_GOVERNMENT_LICENCE_URL,
    attribution=f"{SONIA_ATTRIBUTION} {OPEN_GOVERNMENT_ATTRIBUTION}",
)
GILT_YIELD_RANGE = (-2.0, 20.0)
"""Gilt yields have been as high as 15% and, briefly in 2020, a little below zero."""


def _zero_yield(name: str, years: int) -> ReferenceSeries:
    return ReferenceSeries(
        folder="boe-yield-curve",
        name=name,
        description=f"The {years}-year nominal zero-coupon gilt yield at the end of each month, "
        "continuously compounded, in percent",
        plausible_range=GILT_YIELD_RANGE,
        decimal_places=4,
        credit=YIELD_CURVE_CREDIT,
    )


FIVE_YEAR_ZERO_YIELD = _zero_yield("five_year_zero_yield", 5)
TEN_YEAR_ZERO_YIELD = _zero_yield("ten_year_zero_yield", 10)
TWENTY_YEAR_ZERO_YIELD = _zero_yield("twenty_year_zero_yield", 20)
FIVE_YEAR_PAR_YIELD = ReferenceSeries(
    folder="boe-yield-curve",
    name="five_year_par_yield",
    description="The 5-year nominal par gilt yield at the end of each month, in percent",
    plausible_range=GILT_YIELD_RANGE,
    decimal_places=4,
    credit=YIELD_CURVE_CREDIT,
)
STERLING_CASH_RETURN = ReferenceSeries(
    folder="boe-sterling-cash",
    name="cash_return",
    description="The monthly return on cash earning SONIA, compounded daily, and Bank Rate "
    "before SONIA began",
    plausible_range=(0.0, 0.02),
    decimal_places=10,
    credit=STERLING_CASH_CREDIT,
)
MONTH_END_BANK_RATE = ReferenceSeries(
    folder="boe-sterling-cash",
    name="bank_rate",
    description="Bank Rate at the end of each month, in percent",
    plausible_range=(0.0, 20.0),
    decimal_places=4,
    credit=STERLING_CASH_CREDIT,
)
"""The overnight point of the gilt curve. SONIA's month ends jump about, more so before 2006."""

REFERENCE_SERIES = (
    USD_PER_GBP,
    FIVE_YEAR_ZERO_YIELD,
    TEN_YEAR_ZERO_YIELD,
    TWENTY_YEAR_ZERO_YIELD,
    FIVE_YEAR_PAR_YIELD,
    STERLING_CASH_RETURN,
    MONTH_END_BANK_RATE,
)


def parse_series(series: ReferenceSeries, text: str) -> MonthlySeries:
    """Read a stored series, checking its header, months and values.

    Raises:
        ValueError: If the header is not the series' own, a row is malformed, a value is out of
            the plausible range, or the months have gaps.
    """
    lines = text.splitlines()
    if not lines or lines[0] != series.header:
        raise ValueError(f"{series.path} must start with the header {series.header!r}")
    low, high = series.plausible_range
    pairs: list[tuple[Month, float]] = []
    for number, line in enumerate(lines[1:], start=2):
        month_text, _, value_text = line.partition(",")
        if not _NUMBER.fullmatch(value_text):
            raise ValueError(f"{series.path}:{number}: expected YYYY-MM,<number>")
        value = float(value_text)
        if not low <= value <= high:
            raise ValueError(f"{series.path}:{number}: value outside {low} to {high}")
        pairs.append((Month.parse(month_text), value))
    return MonthlySeries.from_pairs(pairs)


def reference_folder() -> Traversable:
    """The package folder that holds the stored series."""
    return files(__package__).joinpath("reference")


def load(series: ReferenceSeries, folder: Traversable | None = None) -> MonthlySeries:
    """Read a stored series, from the package's reference folder unless another is given."""
    resource = (folder or reference_folder()).joinpath(series.folder, f"{series.name}.csv")
    return parse_series(series, resource.read_text(encoding="utf-8"))


@cache
def stored(series: ReferenceSeries) -> MonthlySeries:
    """Return the package's own copy of a series, read once.

    The files are part of the installed package and never change while the app runs, so each is
    read and checked on first use only.
    """
    return load(series)
