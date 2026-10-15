"""Everything the pages load, cached so that they stay quick. The only Streamlit caching lives here.

Share returns are downloaded from the Kenneth R. French Data Library at most once a day per file and
held in memory only. When a download fails, that file is not tried again for a few minutes, so a
server that is down does not keep every visitor waiting.
"""

import threading
import time
from collections.abc import Callable
from datetime import timedelta

import streamlit as st

from crashmodel.data import client
from crashmodel.data.french import (
    FrenchFile,
    MarketReturns,
    SourceUnavailableError,
    fetch_market_returns,
)
from crashmodel.data.panel import SHARE_FILES, Panel, build_panel

SHARE_DATA_LIFETIME = timedelta(days=1)
"""The library is updated monthly, so a copy up to a day old is current enough."""
RETRY_AFTER = timedelta(minutes=5)
"""How long a file that failed to download is left before it is tried again."""


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


@st.cache_data(ttl=SHARE_DATA_LIFETIME, show_spinner=False)
def _download(file: FrenchFile) -> MarketReturns:
    # A failure raises, and Streamlit caches only results, so the next request tries again.
    with client.make_client() as http_client:
        return fetch_market_returns(http_client, file)


def share_returns(file: FrenchFile) -> MarketReturns | None:
    """Return one file's market returns, or ``None`` if it cannot be fetched just now."""
    failures = _failures()
    if failures.is_waiting(file.url):
        return None
    try:
        return _download(file)
    except SourceUnavailableError:
        failures.record(file.url)
        return None


def load_panel() -> Panel:
    """Return every block's monthly returns in pounds, with whichever share files can be fetched."""
    return build_panel({block: share_returns(file) for block, file in SHARE_FILES.items()})


def try_again() -> None:
    """Forget recent failures, so the next load tries every share file again."""
    _failures().forget()
