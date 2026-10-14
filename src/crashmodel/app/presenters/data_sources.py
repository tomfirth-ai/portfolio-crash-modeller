"""What the Data sources page says about each source the app fetches when it runs."""

from collections.abc import Sequence
from dataclasses import dataclass

from crashmodel.data.diagnostics import Failure, SourceStatus

TITLE = "Data sources"

INTRODUCTION = (
    "Some data is fetched when the app runs rather than stored with it, either because its "
    "publisher allows use but not redistribution, or because it has to be up to date. This page "
    "checks that each source can be reached from wherever the app is running."
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
        used_for=result.source.purpose,
    )


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
