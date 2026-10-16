"""Everything the pages load, cached so that they stay quick. The only Streamlit caching lives here.

Share portfolios are downloaded from the Kenneth R. French Data Library at most once a day per file,
only when a split needs them, and held in memory only. When a download fails, that file is not tried
again for a few minutes, so a server that is down does not keep every visitor waiting; when the
server cannot be reached at all, none of its files is tried.
"""

import logging
import threading
import time
from collections.abc import Callable, Iterable
from datetime import timedelta

import streamlit as st

from crashmodel.data import client, diagnostics
from crashmodel.data.diagnostics import SourceStatus
from crashmodel.data.french import (
    PORTFOLIO_FILES,
    PortfolioFile,
    Portfolios,
    SourceUnavailableError,
    SourceUnreachableError,
    fetch_portfolios,
)
from crashmodel.data.models import IndexModel, files_for
from crashmodel.data.panel import Panel, build_panel

SHARE_DATA_LIFETIME = timedelta(days=1)
"""The library is updated monthly, so a copy up to a day old is current enough."""
RETRY_AFTER = timedelta(minutes=5)
"""How long a file that failed to download is left before it is tried again."""
SOURCE_CHECK_LIFETIME = timedelta(minutes=1)
"""How long the Data sources page reuses a check, so repeated clicks do not load the sources."""

_LOGGER = logging.getLogger(__name__)


class FailureMemory:
    """Which downloads failed recently, so they are not tried on every visit.

    One memory is shared by every visitor, so it is safe to use from several threads at once.
    """

    def __init__(
        self, wait: timedelta = RETRY_AFTER, clock: Callable[[], float] = time.monotonic
    ) -> None:
        """Remember failures for ``wait``, timed by ``clock`` in seconds."""
        self._wait_seconds = wait.total_seconds()
        self._clock = clock
        self._failed_at: dict[str, float] = {}
        self._lock = threading.Lock()

    def record(self, url: str) -> None:
        """Note that a download from ``url`` has just failed."""
        with self._lock:
            self._failed_at[url] = self._clock()

    def is_waiting(self, url: str) -> bool:
        """Whether ``url`` failed so recently that it should not be tried yet."""
        with self._lock:
            failed_at = self._failed_at.get(url)
            return failed_at is not None and self._clock() - failed_at < self._wait_seconds

    def forget(self) -> None:
        """Forget every failure, so each file is tried on its next request."""
        with self._lock:
            self._failed_at.clear()


@st.cache_resource(show_spinner=False)
def _failures() -> FailureMemory:
    return FailureMemory()


class _RecentlyFailedError(Exception):
    """The file failed to download a short while ago, so it is not tried yet."""


@st.cache_data(ttl=SHARE_DATA_LIFETIME, show_spinner=False)
def _download(file: PortfolioFile) -> Portfolios:
    # Checked here, inside the cache, so visitors queued behind a failing download do not each
    # try again. A failure raises, and Streamlit caches only results.
    if _failures().is_waiting(file.url):
        raise _RecentlyFailedError
    with client.make_client() as http_client:
        return fetch_portfolios(http_client, file)


def portfolios(file: PortfolioFile) -> Portfolios | None:
    """Return one file's portfolios, or ``None`` if it cannot be fetched just now."""
    try:
        return _download(file)
    except _RecentlyFailedError:
        return None
    except SourceUnreachableError as error:
        _LOGGER.warning("The share data's server cannot be reached: %s", error)
        # Every file is on that one server, so none is tried until the wait is over.
        for other in PORTFOLIO_FILES:
            _failures().record(other.url)
        return None
    except SourceUnavailableError as error:
        _LOGGER.warning("Share portfolios are unavailable: %s", error)
        _failures().record(file.url)
        return None


def load_panel(models: Iterable[IndexModel]) -> Panel:
    """Return each model's monthly returns in pounds, fetching only the files ``models`` need."""
    return build_panel({file: portfolios(file) for file in files_for(models)})


def try_again() -> None:
    """Forget recent failures, so the next load tries every file again."""
    _failures().forget()


@st.cache_data(ttl=SOURCE_CHECK_LIFETIME, show_spinner=False)
def source_checks() -> list[SourceStatus]:
    """Check that each runtime source can be reached, reusing a check made in the last minute."""
    with client.make_client() as http_client:
        return diagnostics.check_sources(http_client, diagnostics.HOSTED_SOURCES)
