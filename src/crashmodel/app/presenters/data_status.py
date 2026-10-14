"""What the Data status page says about each runtime source."""

from collections.abc import Sequence
from dataclasses import dataclass

from crashmodel.data.diagnostics import SourceStatus

TITLE = "Data sources and status"

INTRODUCTION = (
    "Some history is fetched when the app runs instead of being stored here, because its "
    "publishers allow use but not redistribution. This page checks that each of those sources can "
    "be reached from wherever the app is running."
)

BYTES_PER_KILOBYTE = 1024
MILLISECONDS_PER_SECOND = 1000


@dataclass(frozen=True)
class StatusRow:
    """One row of the status table, ready to display."""

    source: str
    used_for: str
    status: str
    response_time: str
    size: str

    def as_table_row(self) -> dict[str, str]:
        """Return the row keyed by its column headings."""
        return {
            "Source": self.source,
            "Used for": self.used_for,
            "Status": self.status,
            "Response time": self.response_time,
            "Size": self.size,
        }


def status_row(result: SourceStatus) -> StatusRow:
    """Describe one check in words, so the status never depends on colour alone."""
    if result.reachable:
        status = "Reachable"
    elif result.error:
        status = f"Unreachable ({result.error})"
    else:
        status = "Unreachable"
    return StatusRow(
        source=result.source.name,
        used_for=result.source.purpose,
        status=status,
        response_time=""
        if result.elapsed_ms is None
        else f"{result.elapsed_ms / MILLISECONDS_PER_SECOND:.1f} s",
        size=""
        if result.size_bytes is None
        else f"{result.size_bytes / BYTES_PER_KILOBYTE:,.0f} KB",
    )


def status_table(results: Sequence[SourceStatus]) -> list[dict[str, str]]:
    """Return the checks as table rows keyed by column heading."""
    return [status_row(result).as_table_row() for result in results]


def summary(results: Sequence[SourceStatus]) -> str:
    """Summarise the checks in one sentence."""
    reachable = sum(result.reachable for result in results)
    if reachable == len(results):
        return f"All {len(results)} sources are reachable."
    return f"{reachable} of {len(results)} sources are reachable."
