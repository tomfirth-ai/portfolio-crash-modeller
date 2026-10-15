from datetime import timedelta

import pytest

from crashmodel.app import loaders
from crashmodel.app.loaders import FailureMemory
from crashmodel.data import client
from crashmodel.data.blocks import SHARE_BLOCKS
from crashmodel.data.french import DEVELOPED_MARKETS, US_MARKET
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
    first = loaders.share_returns(US_MARKET)
    again = loaders.share_returns(US_MARKET)

    assert first is not None
    assert first == again
    assert first.returns.end == LIBRARY_END
    assert library.requests == [US_MARKET.url]


def test_a_failed_file_is_not_tried_again_until_the_visitor_asks(library: FakeLibrary) -> None:
    library.online = False
    assert loaders.share_returns(DEVELOPED_MARKETS) is None

    library.online = True
    assert loaders.share_returns(DEVELOPED_MARKETS) is None
    assert len(library.requests) == 1

    loaders.try_again()
    assert loaders.share_returns(DEVELOPED_MARKETS) is not None
    assert len(library.requests) == 2


def test_the_panel_has_every_block_when_both_files_arrive(library: FakeLibrary) -> None:
    panel = loaders.load_panel()

    assert panel.unavailable == frozenset()
    assert panel.returns.keys() >= SHARE_BLOCKS
    assert sorted(library.requests) == sorted([US_MARKET.url, DEVELOPED_MARKETS.url])


def test_the_panel_lists_share_blocks_as_unavailable_when_the_library_is_down(
    library: FakeLibrary,
) -> None:
    library.online = False
    assert loaders.load_panel().unavailable == SHARE_BLOCKS
