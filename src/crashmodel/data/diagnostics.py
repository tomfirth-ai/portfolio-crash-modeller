"""Connectivity checks for the data sources the hosted app fetches at runtime.

The hosted demo fetches some data at runtime rather than committing it, either because the
publisher allows use but not redistribution, or because the data has to be up to date. These checks
show whether each source is reachable from wherever the app is running, which matters most on
shared cloud hosts.
"""

import time
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto

import httpx

from crashmodel.data.french import PORTFOLIO_FILES


@dataclass(frozen=True)
class DataSource:
    """A data source the app fetches at runtime."""

    name: str
    url: str


class Failure(Enum):
    """Why a source could not be reached."""

    TIMEOUT = auto()
    """The server took too long to connect or reply."""
    CONNECTION = auto()
    """No connection could be made, or it broke off."""
    ERROR_STATUS = auto()
    """The server replied with an HTTP error status."""
    OTHER = auto()
    """The request failed in some other way, such as too many redirects."""


@dataclass(frozen=True, kw_only=True)
class SourceStatus:
    """The outcome of one connectivity check.

    Attributes:
        source: The source that was checked.
        failure: Why the source could not be reached, or ``None`` if it could.
        status_code: The HTTP status code, if any response came back.
        elapsed_seconds: Time to the full response, if any response came back.
        size_bytes: Size of the response body, if any response came back.
    """

    source: DataSource
    failure: Failure | None = None
    status_code: int | None = None
    elapsed_seconds: float | None = None
    size_bytes: int | None = None

    @property
    def reachable(self) -> bool:
        """Whether a successful response came back."""
        return self.failure is None


HOSTED_SOURCES: tuple[DataSource, ...] = tuple(
    DataSource(name=f"Kenneth R. French Data Library, {file.name}", url=file.url)
    for file in PORTFOLIO_FILES
)
"""Every file the share models are built from."""


def check_source(client: httpx.Client, source: DataSource) -> SourceStatus:
    """Fetch one source and report whether it is reachable, how fast and how large."""
    started = time.perf_counter()
    try:
        response = client.get(source.url)
    except httpx.TimeoutException:
        return SourceStatus(source=source, failure=Failure.TIMEOUT)
    except httpx.TransportError:
        return SourceStatus(source=source, failure=Failure.CONNECTION)
    except httpx.HTTPError:
        return SourceStatus(source=source, failure=Failure.OTHER)
    return SourceStatus(
        source=source,
        failure=None if response.is_success else Failure.ERROR_STATUS,
        status_code=response.status_code,
        elapsed_seconds=time.perf_counter() - started,
        size_bytes=len(response.content),
    )


def check_sources(client: httpx.Client, sources: Iterable[DataSource]) -> list[SourceStatus]:
    """Check each source in turn."""
    return [check_source(client, source) for source in sources]
