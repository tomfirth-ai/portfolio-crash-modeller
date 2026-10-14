from crashmodel.app.journey import JOURNEY, Step
from crashmodel.app.presenters import data_sources, home
from crashmodel.app.presenters.copy import DISCLAIMER, page_title
from crashmodel.data.diagnostics import DataSource, SourceStatus

SOURCE = DataSource("Example source", "https://data.example.com/", "Testing")


def test_the_journey_has_four_steps_in_order() -> None:
    assert [spec.step for spec in JOURNEY] == [
        Step.DESIGN,
        Step.STRESS_TEST,
        Step.DECIDE,
        Step.TRACK,
    ]
    assert [spec.number for spec in JOURNEY] == [1, 2, 3, 4]


def test_home_shows_every_step_from_the_journey_registry() -> None:
    cards = home.home_view().steps
    assert [card.title for card in cards] == ["Design", "Stress-test", "Decide", "Track"]
    assert [card.label for card in cards] == ["Step 1", "Step 2", "Step 3", "Step 4"]


def test_each_page_has_its_own_tab_title() -> None:
    assert page_title("Home") == "Home | Portfolio crash modeller"


def test_the_disclaimer_says_not_investment_advice() -> None:
    assert DISCLAIMER.startswith("Not investment advice.")


def test_reachable_sources_are_described_in_words() -> None:
    row = data_sources.status_row(
        SourceStatus(SOURCE, reachable=True, status_code=200, elapsed_ms=1234.0, size_bytes=4096)
    )
    assert row.as_table_row() == {
        "Source": "Example source",
        "Used for": "Testing",
        "Status": "Reachable",
        "Response time": "1.2 s",
        "Size": "4 KB",
    }


def test_unreachable_sources_give_the_reason() -> None:
    row = data_sources.status_row(SourceStatus(SOURCE, reachable=False, error="ConnectError"))
    assert row.status == "Unreachable (ConnectError)"
    assert row.response_time == ""
    assert row.size == ""


def test_unreachable_sources_without_a_reason() -> None:
    assert data_sources.status_row(SourceStatus(SOURCE, reachable=False)).status == "Unreachable"


def test_summary_counts_reachable_sources() -> None:
    up = SourceStatus(SOURCE, reachable=True)
    down = SourceStatus(SOURCE, reachable=False)
    assert data_sources.summary([up, up]) == "All 2 sources are reachable."
    assert data_sources.summary([up, down]) == "1 of 2 sources are reachable."
