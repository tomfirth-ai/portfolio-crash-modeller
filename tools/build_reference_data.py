"""Download the open data stored with the app, and write it to the reference folder.

Run by hand when the data needs refreshing, never in CI, because it downloads from the publishers:

    python -m tools.build_reference_data                        # retrieved today
    python -m tools.build_reference_data --retrieved 2026-10-15

Each series stops at the last complete month before the retrieval date, and is written as
``YYYY-MM`` rows. Each folder holds the series from one publisher's dataset, with a ``SOURCE.md``
giving how each file was made, the publisher, licence, attribution, retrieval date and the SHA-256
of every file downloaded, so a rebuild can be checked.
"""

import argparse
import hashlib
import io
import sys
import zipfile
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree

import httpx

from crashmodel.data import client as http_client
from crashmodel.data.reference_data import (
    FIVE_YEAR_PAR_YIELD,
    FIVE_YEAR_ZERO_YIELD,
    MONTH_END_BANK_RATE,
    STERLING_CASH_RETURN,
    TEN_YEAR_ZERO_YIELD,
    TWENTY_YEAR_ZERO_YIELD,
    USD_PER_GBP,
    ReferenceSeries,
    parse_series,
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
BANK_RATE_CODE = "IUDBEDR"
SONIA_CODE = "IUDSOIA"
YIELD_CURVE_CODES = {
    FIVE_YEAR_ZERO_YIELD: "IUMSNZC",
    TEN_YEAR_ZERO_YIELD: "IUMMNZC",
    TWENTY_YEAR_ZERO_YIELD: "IUMLNZC",
    FIVE_YEAR_PAR_YIELD: "IUMSNPY",
}
"""The month-end gilt yields the Bank estimates from its yield curve, by the series stored."""

type Observations = list[tuple[date, float]]
type Output = tuple[ReferenceSeries, MonthlySeries, list[Download], str]
"""A series to write: its values, the downloads it came from, and how it was made."""


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


def parse_iadb(text: str, code: str) -> Observations:
    """Read one series from a Bank of England Interactive Database CSV.

    Raises:
        DownloadError: If the file is not that series' CSV, for example an error page.
    """
    lines = text.splitlines()
    if not lines or lines[0] != f"DATE,{code}":
        raise DownloadError(f"expected a Bank of England CSV for {code}")
    observations: Observations = []
    for line in filter(None, lines[1:]):
        day, _, value = line.partition(",")
        try:
            observations.append((datetime.strptime(day, IADB_DATE_FORMAT).date(), float(value)))
        except ValueError:
            raise DownloadError(f"{code}: the row {line!r} is not a date and a number") from None
    return observations


def last_complete_month(retrieved: date) -> Month:
    """Return the last month that had ended before the retrieval date."""
    return Month.of(retrieved).previous


def last_published_month(daily: Sequence[tuple[date, float]]) -> Month:
    """Return the last month whose final daily rate has been published.

    Daily rates are published a few days late, so the newest month may hold only its first days.
    A month counts as complete once a day from a later month has been published.
    """
    return Month.of(daily[-1][0]).previous


def render_series(series: ReferenceSeries, values: MonthlySeries) -> str:
    """Write a series as its header and ``YYYY-MM,<value>`` rows."""
    rows = (f"{month},{value:.{series.decimal_places}f}\n" for month, value in values.items())
    return f"{series.header}\n" + "".join(rows)


def spliced(earlier: Sequence[tuple[date, float]], later: Observations) -> Observations:
    """Join two daily rates: ``earlier`` until the day ``later`` begins, then ``later``."""
    return [observation for observation in earlier if observation[0] < later[0][0]] + later


def render_source(outputs: Sequence[Output], retrieved: date) -> str:
    """Write the ``SOURCE.md`` for a folder of series that share a publisher's dataset.

    Raises:
        ValueError: If the series do not share one credit.
    """
    credits = {series.credit for series, _, _, _ in outputs}
    if len(credits) != 1:
        raise ValueError("every series in a folder must come from the same dataset")
    [credit] = credits
    described = "".join(
        f"  - `{series.name}.csv`, with the header `{series.header}`: {series.description}. "
        f"{method}\n"
        for series, _, _, method in outputs
    )
    downloads = dict.fromkeys(download for _, _, used, _ in outputs for download in used)
    files = "".join(f"  - {download.url}, SHA-256 `{download.sha256}`\n" for download in downloads)
    return (
        f"# {credit.dataset}\n\n"
        f"- **Files**, each with one row per month, written YYYY-MM:\n{described}"
        f"- **Publisher:** {credit.publisher}.\n"
        f"- **Dataset:** {credit.dataset}.\n"
        f"- **Where:** {credit.url}\n"
        f"- **Licence:** {credit.licence}, {credit.licence_url}\n"
        f"- **Attribution:** {credit.attribution}\n"
        f"- **Retrieved:** {retrieved.isoformat()}. Months from {Month.of(retrieved)} on are left "
        "out, because they had not ended.\n"
        f"- **Downloaded files:**\n{files}"
    )


def build(client: httpx.Client, retrieved: date, output: Path) -> list[Path]:
    """Download every source, write each series and each folder's notes, and return the files.

    Raises:
        DownloadError: If a download fails or is not the expected file, or a series fails the
            checks the app makes on loading it; then nothing is written.
    """
    last = last_complete_month(retrieved)
    h10_zip, h10 = _fetch(client, H10_URL)
    with zipfile.ZipFile(io.BytesIO(h10_zip)) as archive:
        daily_rates = parse_h10(archive.read(H10_MEMBER), H10_SERIES)
    bank_rate, bank_rate_download = _iadb(client, BANK_RATE_CODE)
    sonia, sonia_download = _iadb(client, SONIA_CODE)
    cash_rates = spliced(bank_rate, sonia)
    last_cash = min(last, last_published_month(sonia))
    outputs: list[Output] = [
        (
            USD_PER_GBP,
            _up_to(
                _month_ends(daily_rates, H10_SERIES),
                min(last, last_published_month(daily_rates)),
            ),
            [h10],
            f"The last daily rate in each calendar month, from series {H10_SERIES} in the "
            f"release's XML file ({H10_MEMBER}), written to 4 decimal places as published.",
        ),
    ]
    for series, code in YIELD_CURVE_CODES.items():
        yields, download = _iadb(client, code)
        outputs.append(
            (series, _up_to(_month_ends(yields, code), last), [download], _yield_method(code))
        )
    sonia_began = f"{sonia[0][0].day} {sonia[0][0]:%B %Y}"
    outputs += [
        (
            STERLING_CASH_RETURN,
            monthly_cash_returns(cash_rates, last_cash),
            [bank_rate_download, sonia_download],
            f"Daily SONIA (series {SONIA_CODE}) from its first day, {sonia_began}, and the daily "
            f"Official Bank Rate (series {BANK_RATE_CODE}) before it, from the Bank's Interactive "
            f"Database, turned into a monthly return on cash. {_COMPOUNDING} The last month is "
            "the last whose final rate had been published. The returns are worked out by this "
            "project, not by the Bank.",
        ),
        (
            MONTH_END_BANK_RATE,
            _up_to(
                _month_ends(bank_rate, BANK_RATE_CODE), min(last, last_published_month(bank_rate))
            ),
            [bank_rate_download],
            f"The daily Official Bank Rate (series {BANK_RATE_CODE}) from the Bank's Interactive "
            "Database: the last rate in each calendar month, written to 4 decimal places.",
        ),
    ]
    files = _rendered(outputs, retrieved, output)
    for path, text, encoding in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding)
    return [path for path, _, _ in files]


def _rendered(outputs: list[Output], retrieved: date, output: Path) -> list[tuple[Path, str, str]]:
    """Render every series and each folder's note, as (path, text, encoding), checking each series.

    Every file is rendered and checked before any is written, so a failed check leaves the stored
    data as it was, with each note still describing the files beside it.

    Raises:
        DownloadError: If a series fails the checks the app makes on loading it.
    """
    by_folder: defaultdict[str, list[Output]] = defaultdict(list)
    for folder_output in outputs:
        by_folder[folder_output[0].folder].append(folder_output)
    files: list[tuple[Path, str, str]] = []
    for folder_name, folder_outputs in by_folder.items():
        folder = output / folder_name
        for series, values, _, _ in folder_outputs:
            text = render_series(series, values)
            try:
                parse_series(series, text)
            except ValueError as error:
                raise DownloadError(str(error)) from None
            files.append((folder / f"{series.name}.csv", text, "ascii"))
        files.append((folder / "SOURCE.md", render_source(folder_outputs, retrieved), "utf-8"))
    return files


_COMPOUNDING = (
    "Each calendar day earns the rate in force that day, rate / 100 / 365, compounded daily. "
    "The first month is the first with a rate on its first day."
)


def _yield_method(code: str) -> str:
    return (
        f"The end-of-month yield (series {code}) from the Bank's Interactive Database, written to "
        "4 decimal places. The Bank drops trailing zeros."
    )


def _month_ends(observations: Observations, code: str) -> MonthlySeries:
    """The last rate in each month, refusing a month the publisher left out."""
    try:
        return month_end_rates(observations)
    except ValueError as error:
        raise DownloadError(f"{code}: {error}") from None


def _iadb(client: httpx.Client, code: str) -> tuple[Observations, Download]:
    """Download and read one series from the Bank of England's Interactive Database."""
    csv, download = _fetch(client, IADB_URL, _iadb_query(code))
    return parse_iadb(csv.decode(), code), download


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
