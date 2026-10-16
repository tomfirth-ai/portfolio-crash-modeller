import pytest

from crashmodel.app.journey import JOURNEY
from crashmodel.app.presenters import data_sources, home
from crashmodel.app.presenters.copy import DISCLAIMER, page_title
from crashmodel.data.diagnostics import HOSTED_SOURCES, DataSource, Failure, SourceStatus
from crashmodel.data.reference_data import GILT_YIELD, REFERENCE_SERIES

SOURCE = DataSource("Example source", "https://data.example.com/")


def test_the_journey_has_four_steps_in_order() -> None:
    assert [spec.title for spec in JOURNEY] == ["Design", "Stress-test", "Decide", "Track"]


def test_home_shows_every_step_from_the_journey_registry() -> None:
    cards = home.home_view().steps
    assert [card.title for card in cards] == ["Design", "Stress-test", "Decide", "Track"]
    assert [card.label for card in cards] == ["Step 1", "Step 2", "Step 3", "Step 4"]


def test_each_page_has_its_own_tab_title() -> None:
    assert page_title("Home") == "Home | Portfolio crash modeller"


def test_the_disclaimer_says_not_investment_advice() -> None:
    assert DISCLAIMER.startswith("Not investment advice.")


def test_reachable_sources_are_described_in_words_with_the_answer_first() -> None:
    result = SourceStatus(source=SOURCE, status_code=200, elapsed_seconds=1.234, size_bytes=4096)
    assert data_sources.status_row(result).as_table_row() == {
        "Source": "Example source",
        "Status": "Reachable",
        "Response time": "1.2\u00a0s",
        "Size": "4\u00a0KB",
        "Used for": "",
    }


def test_each_source_names_every_index_whose_model_is_built_from_it() -> None:
    assert [data_sources.used_for(source) for source in HOSTED_SOURCES] == [
        "The models of S&P 500",
        "The models of MSCI World, FTSE Developed, FTSE All-World, MSCI ACWI, FTSE Global All Cap "
        "and MSCI ACWI IMI",
        "The models of FTSE All-World, MSCI ACWI, FTSE Global All Cap and MSCI ACWI IMI",
    ]


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (Failure.TIMEOUT, "Unreachable: timed out"),
        (Failure.CONNECTION, "Unreachable: could not connect"),
        (Failure.ERROR_STATUS, "Unreachable: the server replied with HTTP 503"),
        (Failure.OTHER, "Unreachable: the request failed"),
    ],
)
def test_unreachable_sources_say_why_in_plain_words(failure: Failure, status: str) -> None:
    result = SourceStatus(source=SOURCE, failure=failure, status_code=503)
    assert data_sources.describe_status(result) == status


def test_timing_and_size_are_blank_without_a_response() -> None:
    row = data_sources.status_row(SourceStatus(source=SOURCE, failure=Failure.CONNECTION))
    assert (row.response_time, row.size) == ("", "")


@pytest.mark.parametrize(
    ("seconds", "shown"), [(0.042, "42 ms"), (0.9994, "999 ms"), (1.0, "1.0 s"), (12.34, "12.3 s")]
)
def test_durations_use_milliseconds_below_a_second(seconds: float, shown: str) -> None:
    assert data_sources.format_duration(seconds) == shown.replace(" ", "\u00a0")


@pytest.mark.parametrize(
    ("size_bytes", "shown"),
    [(0, "0 bytes"), (1, "1 byte"), (300, "300 bytes"), (4096, "4 KB"), (2_621_440, "2.5 MB")],
)
def test_sizes_use_the_unit_that_reads_best(size_bytes: int, shown: str) -> None:
    assert data_sources.format_size(size_bytes) == shown.replace(" ", "\u00a0")


UP = SourceStatus(source=SOURCE)
DOWN = SourceStatus(source=SOURCE, failure=Failure.CONNECTION)


@pytest.mark.parametrize(
    ("results", "sentence"),
    [
        ([], "There are no sources to check."),
        ([UP], "The source is reachable."),
        ([UP, UP], "All 2 sources are reachable."),
        ([UP, DOWN], "1 of 2 sources is reachable."),
        ([DOWN, DOWN], "0 of 2 sources are reachable."),
    ],
)
def test_the_summary_agrees_in_number(results: list[SourceStatus], sentence: str) -> None:
    assert data_sources.summary(results) == sentence


def test_each_stored_series_is_credited_with_links_to_its_publisher_and_licence() -> None:
    row = data_sources.stored_row(GILT_YIELD)
    assert row == {
        "Data": GILT_YIELD.description,
        "Publisher": f"[Bank of England]({GILT_YIELD.credit.url})",
        "Licence": f"[Open Government Licence v3.0]({GILT_YIELD.credit.licence_url})",
        "Attribution": GILT_YIELD.credit.attribution,
    }
    assert len(data_sources.stored_table()) == len(REFERENCE_SERIES)
