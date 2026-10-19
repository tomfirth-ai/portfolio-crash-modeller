from datetime import timedelta

import pytest
from streamlit.runtime.caching.cache_data_api import CachedDataFuncInfo

from crashmodel.app import loaders
from crashmodel.app.loaders import FailureMemory
from crashmodel.data import client
from crashmodel.data.french import DEVELOPED_BY_SIZE, EMERGING_BY_SIZE, US_BY_SIZE
from crashmodel.data.models import IndexModel
from tests.data.french_text import LIBRARY_END, FakeLibrary

URL = "https://data.example.com/file.zip"


class Clock:
    def __init__(self) -> None:
        self.seconds = 0.0

    def __call__(self) -> float:
        return self.seconds


def test_a_failure_is_remembered_until_the_wait_is_over() -> None:
    clock = Clock()
    memory = FailureMemory(wait=timedelta(minutes=5), clock=clock)
    assert not memory.is_waiting(URL)

    memory.record(URL)
    clock.seconds = 299.0
    assert memory.is_waiting(URL)
    assert not memory.is_waiting("https://data.example.com/other.zip")

    clock.seconds = 300.0
    assert not memory.is_waiting(URL)


def test_forgetting_clears_every_failure() -> None:
    memory = FailureMemory(clock=Clock())
    memory.record(URL)
    memory.forget()
    assert not memory.is_waiting(URL)


@pytest.fixture
def library(monkeypatch: pytest.MonkeyPatch) -> FakeLibrary:
    fake = FakeLibrary()
    monkeypatch.setattr(client, "make_client", fake.client)
    return fake


def test_each_file_is_downloaded_once_and_then_served_from_the_cache(library: FakeLibrary) -> None:
    first = loaders.portfolios(US_BY_SIZE)
    again = loaders.portfolios(US_BY_SIZE)

    assert first is not None
    assert first == again
    assert first.portfolios["Hi 10"].returns.end == LIBRARY_END
    assert library.requests == [US_BY_SIZE.url]


def test_a_failed_file_is_not_tried_again_until_the_visitor_asks(library: FakeLibrary) -> None:
    library.online = False
    assert loaders.portfolios(DEVELOPED_BY_SIZE) is None

    library.online = True
    assert loaders.portfolios(DEVELOPED_BY_SIZE) is None
    assert len(library.requests) == 1

    loaders.try_again()
    assert loaders.portfolios(DEVELOPED_BY_SIZE) is not None
    assert len(library.requests) == 2


def test_only_the_files_the_held_models_need_are_fetched(library: FakeLibrary) -> None:
    panel = loaders.load_panel({IndexModel.GLOBAL_LARGE, IndexModel.STERLING_CASH})

    assert panel.unavailable == frozenset()
    assert IndexModel.GLOBAL_LARGE in panel.returns
    assert IndexModel.US_LARGE not in panel.returns
    assert library.requests == [DEVELOPED_BY_SIZE.url, EMERGING_BY_SIZE.url]


def test_splits_of_gilts_and_cash_fetch_nothing(library: FakeLibrary) -> None:
    loaders.load_panel({IndexModel.UK_GILTS_ALL, IndexModel.STERLING_CASH})
    assert library.requests == []


def test_the_held_share_models_are_unavailable_when_the_library_is_down(
    library: FakeLibrary,
) -> None:
    library.online = False
    panel = loaders.load_panel({IndexModel.US_LARGE, IndexModel.UK_GILTS_ALL})
    assert panel.unavailable == {IndexModel.US_LARGE}
    assert IndexModel.UK_GILTS_ALL in panel.returns


def test_once_the_server_cannot_be_reached_its_other_files_are_not_tried(
    library: FakeLibrary,
) -> None:
    library.online = False
    panel = loaders.load_panel({IndexModel.GLOBAL_ALL_CAP, IndexModel.US_LARGE})
    assert {IndexModel.GLOBAL_ALL_CAP, IndexModel.US_LARGE} <= panel.unavailable
    assert len(library.requests) == 1


def test_a_file_that_fails_on_its_own_leaves_the_others_to_be_fetched(
    library: FakeLibrary,
) -> None:
    library.moved.add(US_BY_SIZE.url)
    panel = loaders.load_panel({IndexModel.US_LARGE, IndexModel.GLOBAL_LARGE})
    assert IndexModel.US_LARGE in panel.unavailable
    assert IndexModel.GLOBAL_LARGE in panel.returns
    assert library.requests == [US_BY_SIZE.url, DEVELOPED_BY_SIZE.url, EMERGING_BY_SIZE.url]


def test_share_data_is_cached_in_memory_only() -> None:
    """French data may never be written to disk, so the cache must not persist it."""
    info = loaders._download._info
    assert isinstance(info, CachedDataFuncInfo)
    assert info.persist is None


def test_when_a_refresh_fails_the_last_good_copy_is_used(library: FakeLibrary) -> None:
    first = loaders.portfolios(US_BY_SIZE)
    loaders._download.clear()  # The day is over, so the next request downloads again.
    library.online = False

    assert loaders.portfolios(US_BY_SIZE) == first
    panel = loaders.load_panel({IndexModel.US_LARGE})
    assert panel.unavailable == frozenset()
    assert len(library.requests) == 2


def test_a_file_never_downloaded_has_no_copy_to_fall_back_on(library: FakeLibrary) -> None:
    library.online = False
    assert loaders.portfolios(US_BY_SIZE) is None


def test_a_new_store_holds_no_copies() -> None:
    copies = loaders.LastGoodCopies()
    assert copies.get(US_BY_SIZE) is None


def test_when_one_file_fails_on_its_own_its_last_good_copy_is_used(library: FakeLibrary) -> None:
    first = loaders.portfolios(US_BY_SIZE)
    loaders._download.clear()
    library.moved.add(US_BY_SIZE.url)

    assert loaders.portfolios(US_BY_SIZE) == first
    assert loaders.load_panel({IndexModel.US_LARGE}).unavailable == frozenset()


@pytest.mark.usefixtures("library")
def test_a_newer_download_replaces_the_copy_kept_before_it() -> None:
    older, newer = loaders.portfolios(US_BY_SIZE), loaders.portfolios(DEVELOPED_BY_SIZE)
    assert older is not None
    assert newer is not None
    copies = loaders.LastGoodCopies()
    copies.keep(US_BY_SIZE, older)
    copies.keep(US_BY_SIZE, newer)
    assert copies.get(US_BY_SIZE) is newer
