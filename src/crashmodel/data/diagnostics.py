"""Connectivity checks for the data sources the hosted app fetches at runtime.

The hosted demo fetches some data at runtime rather than committing it, either because the
publisher allows use but not redistribution, or because the data has to be up to date. These checks
show whether each source is reachable from wherever the app is running, which matters most on
shared cloud hosts.
"""

import time
from collections.abc import Iterable
from dataclasses import dataclass

import httpx

from crashmodel.project import user_agent

DEFAULT_TIMEOUT_SECONDS = 10.0
MILLISECONDS_PER_SECOND = 1000


@dataclass(frozen=True)
class DataSource:
    """A runtime data source and why the app needs it."""

    name: str
    url: str
    purpose: str


@dataclass(frozen=True)
class SourceStatus:
    """The outcome of one connectivity check.

    Attributes:
        source: The source that was checked.
        reachable: Whether a successful HTTP response came back.
        status_code: The HTTP status code, if any response came back.
        elapsed_ms: Time to the full response in milliseconds, if any response came back.
        size_bytes: Size of the response body, if any response came back.
        error: A short reason when the source was not reachable.
    """

    source: DataSource
    reachable: bool
    status_code: int | None = None
    elapsed_ms: float | None = None
    size_bytes: int | None = None
    error: str | None = None


HOSTED_SOURCES: tuple[DataSource, ...] = (
    DataSource(
        name="Kenneth R. French Data Library",
        url="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip",
        purpose="Share price history for the crash episodes",
    ),
    DataSource(
        name="Federal Reserve Board H.10",
        url="https://www.federalreserve.gov/releases/h10/hist/dat00_uk.htm",
        purpose="Recent exchange rates between the pound and the dollar",
    ),
)


def make_client(timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> httpx.Client:
    """Return an HTTP client that identifies the project and follows redirects."""
    return httpx.Client(
        timeout=timeout_seconds, follow_redirects=True, headers={"User-Agent": user_agent()}
    )


def check_source(client: httpx.Client, source: DataSource) -> SourceStatus:
    """Fetch one source and report whether it is reachable, how fast and how large."""
    started = time.perf_counter()
    try:
        response = client.get(source.url)
    except httpx.HTTPError as error:
        return SourceStatus(source, reachable=False, error=type(error).__name__)
    elapsed_ms = (time.perf_counter() - started) * MILLISECONDS_PER_SECOND
    return SourceStatus(
        source,
        reachable=response.is_success,
        status_code=response.status_code,
        elapsed_ms=elapsed_ms,
        size_bytes=len(response.content),
        error=None if response.is_success else response.reason_phrase,
    )


def check_sources(client: httpx.Client, sources: Iterable[DataSource]) -> list[SourceStatus]:
    """Check each source in turn."""
    return [check_source(client, source) for source in sources]
