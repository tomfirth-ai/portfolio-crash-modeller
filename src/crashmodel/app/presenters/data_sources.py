"""What the Data sources page says: the open data stored with the app, and what it fetches."""

from collections.abc import Sequence
from dataclasses import dataclass

from crashmodel.app.presenters.format import listed
from crashmodel.data.catalogue import TRACKED_INDEXES
from crashmodel.data.diagnostics import DataSource, Failure, SourceStatus
from crashmodel.data.french import LIBRARY_URL
from crashmodel.data.models import SHARE_MODEL_FILES
from crashmodel.data.reference_data import REFERENCE_SERIES, ReferenceSeries

TITLE = "Data sources"

INTRODUCTION = (
    "The app uses two kinds of data: open data stored with it, and share data fetched when it "
    "runs. Every fund and index is modelled from them; no index values or fund prices are used."
)

STORED_HEADING = "Stored with the app"
STORED_INTRODUCTION = (
    "Open data that its publishers allow anyone to reuse. Each series is stored with its "
    "source, licence and download date recorded beside it."
)
STORED_COLUMNS = ("Data", "Publisher", "Licence", "Attribution")
BOND_METHOD = (
    "UK government bond returns are worked out from the Bank of England's gilt yield curve: a "
    "ladder of gilts valued off the zero-coupon yields for all maturities and for over 15 years, "
    "and for up to 5 years half a 5-year gilt, by the formula of "
    "[Swinkels' government bond returns dataset](https://doi.org/10.25397/eur.8152748) described "
    "in [Swinkels (2019)](https://doi.org/10.3390/data4030091), and half cash earning SONIA. Only "
    "the method of that dataset is used; none of it is stored. The returns on cash and gilts are "
    "worked out by this app, not by the Bank."
)

FETCHED_HEADING = "Fetched when the app runs"
FETCHED_INTRODUCTION = (
    f"The share models are built from the [Kenneth R. French Data Library]({LIBRARY_URL})'s "
    "portfolios of companies grouped by size, with each portfolio's number of firms and their "
    "average market value. They are free to download, but no licence is given to pass them on, "
    "so the app fetches them when it runs, keeps them in memory for up to a day and never stores "
    "them. The check below shows whether each file can be reached from wherever the app is "
    "running."
)

CHECK_BUTTON = "Check the sources"
CHECKING = "Checking each source..."

REACHABLE = "Reachable"
FAILURE_REASONS = {
    Failure.TIMEOUT: "timed out",
    Failure.CONNECTION: "could not connect",
    Failure.OTHER: "the request failed",
}

BYTES_PER_KILOBYTE = 1024
BYTES_PER_MEGABYTE = BYTES_PER_KILOBYTE * 1024
MILLISECONDS_PER_SECOND = 1000
UNIT_SPACE = "\u00a0"
"""A non-breaking space, so a figure and its unit never wrap onto separate lines."""


@dataclass(frozen=True, kw_only=True)
class StatusRow:
    """One row of the status table, ready to display."""

    source: str
    status: str
    response_time: str
    size: str
    used_for: str

    def as_table_row(self) -> dict[str, str]:
        """Return the row keyed by its column headings, with the answer first."""
        return {
            "Source": self.source,
            "Status": self.status,
            "Response time": self.response_time,
            "Size": self.size,
            "Used for": self.used_for,
        }


def describe_status(result: SourceStatus) -> str:
    """Say in words whether a source is reachable and, if not, why, so colour is never needed."""
    match result.failure:
        case None:
            return REACHABLE
        case Failure.ERROR_STATUS:
            return f"Unreachable: the server replied with HTTP {result.status_code}"
        case failure:
            return f"Unreachable: {FAILURE_REASONS[failure]}"


def format_duration(seconds: float) -> str:
    """Show a duration in milliseconds below one second, and in seconds above."""
    if seconds < 1:
        return f"{seconds * MILLISECONDS_PER_SECOND:.0f}{UNIT_SPACE}ms"
    return f"{seconds:.1f}{UNIT_SPACE}s"


def format_size(size_bytes: int) -> str:
    """Show a size in bytes, kilobytes or megabytes, whichever reads best."""
    if size_bytes < BYTES_PER_KILOBYTE:
        unit = "byte" if size_bytes == 1 else "bytes"
        return f"{size_bytes}{UNIT_SPACE}{unit}"
    if size_bytes < BYTES_PER_MEGABYTE:
        return f"{size_bytes / BYTES_PER_KILOBYTE:,.0f}{UNIT_SPACE}KB"
    return f"{size_bytes / BYTES_PER_MEGABYTE:,.1f}{UNIT_SPACE}MB"


def status_row(result: SourceStatus) -> StatusRow:
    """Describe one check, leaving timing and size blank when no response came back."""
    return StatusRow(
        source=result.source.name,
        status=describe_status(result),
        response_time=""
        if result.elapsed_seconds is None
        else format_duration(result.elapsed_seconds),
        size="" if result.size_bytes is None else format_size(result.size_bytes),
        used_for=used_for(result.source),
    )


def used_for(source: DataSource) -> str:
    """Name the indexes whose models are built from a source, or nothing for any other source."""
    models = {
        model
        for model, files in SHARE_MODEL_FILES.items()
        if source.url in {file.url for file in files}
    }
    indexes = [index.name for index in TRACKED_INDEXES if index.model in models]
    return f"The models of {listed(indexes)}" if indexes else ""


def status_table(results: Sequence[SourceStatus]) -> list[dict[str, str]]:
    """Return the checks as table rows keyed by column heading."""
    return [status_row(result).as_table_row() for result in results]


def summary(results: Sequence[SourceStatus]) -> str:
    """Summarise the checks in one sentence."""
    total = len(results)
    reachable = sum(result.reachable for result in results)
    if total == 0:
        return "There are no sources to check."
    if reachable == total:
        return "The source is reachable." if total == 1 else f"All {total} sources are reachable."
    verb = "is" if reachable == 1 else "are"
    return f"{reachable} of {total} sources {verb} reachable."


def stored_row(series: ReferenceSeries) -> dict[str, str]:
    """One stored series' credits, linking to its publisher and its licence."""
    credit = series.credit
    cells = (
        series.description,
        f"[{credit.publisher}]({credit.url})",
        f"[{credit.licence}]({credit.licence_url})",
        credit.attribution,
    )
    return dict(zip(STORED_COLUMNS, cells, strict=True))


def stored_table() -> list[dict[str, str]]:
    """Every series stored with the app, as table rows keyed by column heading."""
    return [stored_row(series) for series in REFERENCE_SERIES]
