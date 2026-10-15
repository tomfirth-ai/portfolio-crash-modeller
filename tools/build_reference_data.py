"""Download the open data stored with the app, and write it to the reference folder.

Run by hand when the data needs refreshing, never in CI, because it downloads from the publishers:

    python -m tools.build_reference_data                        # retrieved today
    python -m tools.build_reference_data --retrieved 2026-10-15

Each series stops at the last complete month before the retrieval date, and is written as
``YYYY-MM`` rows with a ``SOURCE.md`` beside it giving the publisher, licence, attribution,
retrieval date and the SHA-256 of every file downloaded, so a rebuild can be checked.
"""

import argparse
import hashlib
import io
import sys
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree

import httpx

from crashmodel.data import client as http_client
from crashmodel.data.reference_data import (
    CASH_RETURN,
    GILT_YIELD,
    USD_PER_GBP,
    ReferenceSeries,
)
from crashmodel.engine.cash import monthly_cash_returns
from crashmodel.engine.currency import month_end_rates
from crashmodel.engine.months import Month, MonthlySeries

REFERENCE_FOLDER = Path(__file__).resolve().parents[1] / "src/crashmodel/data/reference"
HTTP_OK = 200

H10_URL = "https://www.federalreserve.gov/releases/h10/data/FRB_h10_xml.zip"
H10_MEMBER = "H10_data.xml"
H10_SERIES = "RXI$US_N.B.UK"
"""The pound in US dollars per pound, daily. The file also holds monthly and annual averages."""

IADB_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
IADB_FIRST_DATE = "01/Jan/1975"
IADB_DATE_FORMAT = "%d %b %Y"
GILT_YIELD_CODE = "IUMMNPY"
BANK_RATE_CODE = "IUDBEDR"


class DownloadError(Exception):
    """A publisher's file could not be downloaded or was not what was expected."""


@dataclass(frozen=True)
class Download:
    """A file downloaded from a publisher, and its SHA-256 for checking a rebuild."""

    url: str
    sha256: str


def parse_h10(xml: bytes, series_name: str) -> list[tuple[date, float]]:
    """Read one daily series from the Federal Reserve's H.10 XML file, skipping days with no data.

    Raises:
        DownloadError: If the series does not appear exactly once.
    """
    found: list[list[tuple[date, float]]] = []
    # The file comes over HTTPS from the Federal Reserve. Python 3.12's expat resists entity
    # expansion attacks, and ElementTree never fetches external entities.
    for _, element in ElementTree.iterparse(io.BytesIO(xml), events=("end",)):  # noqa: S314
        if element.tag.endswith("}Series"):
            if element.get("SERIES_NAME") == series_name:
                found.append(
                    [
                        (
                            date.fromisoformat(obs.get("TIME_PERIOD", "")),
                            float(obs.get("OBS_VALUE", "")),
                        )
                        for obs in element
                        if obs.tag.endswith("}Obs") and obs.get("OBS_STATUS") != "ND"
                    ]
                )
            element.clear()
    if len(found) != 1:
        raise DownloadError(
            f"expected series {series_name} once in the H.10 file, found {len(found)}"
        )
    return found[0]


def parse_iadb(text: str, code: str) -> list[tuple[date, float]]:
    """Read one series from a Bank of England Interactive Database CSV.

    Raises:
        DownloadError: If the file is not that series' CSV, for example an error page.
    """
    lines = text.splitlines()
    if not lines or lines[0] != f"DATE,{code}":
        raise DownloadError(f"expected a Bank of England CSV for {code}")
    observations: list[tuple[date, float]] = []
    for line in filter(None, lines[1:]):
        day, _, value = line.partition(",")
        observations.append((datetime.strptime(day, IADB_DATE_FORMAT).date(), float(value)))
    return observations


def last_complete_month(retrieved: date) -> Month:
    """Return the last month that had ended before the retrieval date."""
    return Month.of(retrieved).previous


def render_series(series: ReferenceSeries, values: MonthlySeries) -> str:
    """Write a series as its header and ``YYYY-MM,<value>`` rows."""
    rows = (f"{month},{value:.{series.decimal_places}f}\n" for month, value in values.items())
    return f"{series.header}\n" + "".join(rows)


def render_source(
    series: ReferenceSeries, downloads: Sequence[Download], retrieved: date, method: str
) -> str:
    """Write the ``SOURCE.md`` that sits beside a series."""
    credit = series.credit
    files = "".join(f"  - {download.url}, SHA-256 `{download.sha256}`\n" for download in downloads)
    return (
        f"# {series.description}\n\n"
        f"- **File:** `{series.name}.csv`, with the header `{series.header}` and one row per "
        "month, written YYYY-MM.\n"
        f"- **Publisher:** {credit.publisher}.\n"
        f"- **Dataset:** {credit.dataset}.\n"
        f"- **Where:** {credit.url}\n"
        f"- **Licence:** {credit.licence}, {credit.licence_url}\n"
        f"- **Attribution:** {credit.attribution}\n"
        f"- **Retrieved:** {retrieved.isoformat()}. Months from {Month.of(retrieved)} on are left "
        "out, because they had not ended.\n"
        f"- **Downloaded files:**\n{files}"
        f"- **How it was made:** {method}\n"
    )


def build(client: httpx.Client, retrieved: date, output: Path) -> list[Path]:
    """Download every source, write each series and its ``SOURCE.md``, and return the files.

    Raises:
        DownloadError: If a download fails or is not the expected file.
    """
    last = last_complete_month(retrieved)
    h10_zip, h10 = _fetch(client, H10_URL)
    with zipfile.ZipFile(io.BytesIO(h10_zip)) as archive:
        rates = month_end_rates(parse_h10(archive.read(H10_MEMBER), H10_SERIES))
    gilt_csv, gilt = _fetch(client, IADB_URL, _iadb_query(GILT_YIELD_CODE))
    yields = month_end_rates(parse_iadb(gilt_csv.decode(), GILT_YIELD_CODE))
    bank_rate_csv, bank_rate = _fetch(client, IADB_URL, _iadb_query(BANK_RATE_CODE))
    cash = monthly_cash_returns(parse_iadb(bank_rate_csv.decode(), BANK_RATE_CODE), last)
    outputs = [
        (
            USD_PER_GBP,
            _up_to(rates, last),
            [h10],
            f"The last daily rate in each calendar month, from series {H10_SERIES} in the "
            f"release's XML file ({H10_MEMBER}), written to 4 decimal places as published.",
        ),
        (
            GILT_YIELD,
            _up_to(yields, last),
            [gilt],
            f"The end-of-month yield (series {GILT_YIELD_CODE}) from the Bank's Interactive "
            "Database, written to 4 decimal places. The Bank drops trailing zeros.",
        ),
        (
            CASH_RETURN,
            cash,
            [bank_rate],
            f"The daily Official Bank Rate (series {BANK_RATE_CODE}) from the Bank's Interactive "
            "Database, turned into a monthly return on cash: interest accrues each calendar day "
            "at the rate in force that day, rate / 100 / 365, and is credited at the month end. "
            "The first month is the first with a rate on its first day.",
        ),
    ]
    written: list[Path] = []
    for series, values, downloads, method in outputs:
        folder = output / series.folder
        folder.mkdir(parents=True, exist_ok=True)
        data_file, source_file = folder / f"{series.name}.csv", folder / "SOURCE.md"
        data_file.write_text(render_series(series, values), encoding="ascii")
        source_file.write_text(
            render_source(series, downloads, retrieved, method), encoding="utf-8"
        )
        written += [data_file, source_file]
    return written


def _up_to(values: MonthlySeries, last: Month) -> MonthlySeries:
    """Cut a series at ``last``, or keep all of it if the publisher has not reached ``last`` yet."""
    return values.between(values.start, min(values.end, last))


def _iadb_query(code: str) -> dict[str, str]:
    return {
        "csv.x": "yes",
        "Datefrom": IADB_FIRST_DATE,
        "Dateto": "now",
        "SeriesCodes": code,
        "CSVF": "TN",
        "UsingCodes": "Y",
        "VPD": "Y",
        "VFD": "N",
    }


def _fetch(
    client: httpx.Client, url: str, params: dict[str, str] | None = None
) -> tuple[bytes, Download]:
    # Redirects are not followed: the Bank of England answers a bad request by redirecting to an
    # error page.
    response = client.get(url, params=params, follow_redirects=False)
    if response.status_code != HTTP_OK:
        raise DownloadError(f"{response.request.url} answered HTTP {response.status_code}")
    content = response.content
    return content, Download(str(response.request.url), hashlib.sha256(content).hexdigest())


def main(
    argv: Sequence[str] | None = None,
    make_client: Callable[[], httpx.Client] = http_client.make_client,
) -> int:
    """Download and write every series, and return a process exit code."""
    parser = argparse.ArgumentParser(description="Download the open data stored with the app.")
    parser.add_argument(
        "--retrieved",
        type=date.fromisoformat,
        default=date.today(),
        help="retrieval date (default: today); months from this one on are left out",
    )
    parser.add_argument("--output", type=Path, default=REFERENCE_FOLDER, help="reference folder")
    args = parser.parse_args(argv)
    with make_client() as client:
        try:
            written = build(client, args.retrieved, args.output)
        except (DownloadError, httpx.HTTPError) as error:
            print(f"build reference data: {error}", file=sys.stderr)
            return 1
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
