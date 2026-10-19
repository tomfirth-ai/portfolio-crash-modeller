"""Smoke tests that run the real Streamlit app in-process, with the network blocked."""

import ast
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from crashmodel.app import state
from crashmodel.app.components import footer
from crashmodel.app.presenters import data_sources, design, home, stress_test
from crashmodel.app.presenters.copy import DISCLAIMER, SOURCE_CODE
from crashmodel.app.splits import EXAMPLE_SPLITS
from crashmodel.app.state import percent_key, widget_key
from crashmodel.data import client, diagnostics
from crashmodel.data.reference_data import REFERENCE_SERIES
from crashmodel.engine.episodes import COVID
from tests.app.copy_rules import copy_problems
from tests.app.running import (
    DATA_SOURCES_PAGE,
    DESIGN_PAGE,
    PAGES,
    STRESS_TEST_PAGE,
    button,
    button_group,
    button_groups,
    captions,
    click,
    run_app,
)
from tests.data.french_text import FakeLibrary


def test_home_explains_the_journey() -> None:
    app = run_app()

    assert app.title[0].value == "How would your investments have coped with a crash?"
    steps = [subheader.value for subheader in app.subheader]
    assert steps == ["Design", "Stress-test", "Decide", "Track"]
    badges = [text.value for text in app.markdown if home.COMING_NEXT in text.value]
    assert len(badges) == 2


def test_the_first_button_on_home_opens_the_stress_test(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client, "make_client", FakeLibrary().client)
    app = click(run_app(), home.home_view().first_step)

    assert app.title[0].value == stress_test.TITLE


def test_the_second_button_on_home_opens_the_design() -> None:
    app = click(run_app(), home.home_view().second_step)

    assert app.title[0].value == design.TITLE


def test_home_shows_the_disclaimer() -> None:
    assert DISCLAIMER in captions(run_app())


def offline_client() -> httpx.Client:
    def refuse(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network blocked in tests")

    return httpx.Client(transport=httpx.MockTransport(refuse))


def checked_data_sources_page(monkeypatch: pytest.MonkeyPatch) -> AppTest:
    """The Data sources page after its check has run, with the network refused."""
    monkeypatch.setattr(client, "make_client", offline_client)
    app = run_app(DATA_SOURCES_PAGE)
    return button(app, data_sources.CHECK_BUTTON).click().run()


def rendered_text(app: AppTest) -> list[str]:
    """Every piece of text the page shows: headings, prose, controls, links and table cells."""
    kinds = ("title", "header", "subheader", "markdown", "caption", "info", "warning", "error")
    texts = [element.value for kind in kinds for element in getattr(app, kind)]
    texts += [button.label for button in app.button]
    for group in button_groups(app):
        texts += [group.proto.label, *group.options]
    for kind in ("text_input", "number_input", "toggle", "selectbox", "multiselect"):
        texts += [text for widget in getattr(app, kind) for text in (widget.label, widget.help)]
    for menu in [*app.selectbox, *app.multiselect]:
        texts += [*menu.options, menu.placeholder]
    texts += [bar.proto.text for bar in app.get("progress")]
    texts += [link.proto.label for link in app.get("page_link")]
    for table in app.table:
        texts += [str(cell) for cell in [*table.value.columns, *table.value.to_numpy().ravel()]]
    return texts


def test_data_sources_reports_unreachable_sources_without_failing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = checked_data_sources_page(monkeypatch)

    sources = len(diagnostics.HOSTED_SOURCES)
    assert not app.exception
    assert f"0 of {sources} sources are reachable." in [markdown.value for markdown in app.markdown]
    assert list(app.table[-1].value["Status"]) == ["Unreachable: could not connect"] * sources
    assert DISCLAIMER in captions(app)


def test_data_sources_credits_the_data_stored_with_the_app() -> None:
    app = run_app(DATA_SOURCES_PAGE)

    stored = app.table[0].value
    assert list(stored["Data"]) == [series.description for series in REFERENCE_SERIES]
    assert not app.exception


def fail(*_args: object) -> None:
    raise RuntimeError("a page bug")


def stop(*_args: object) -> None:
    st.stop()


@pytest.mark.parametrize("check_sources", [fail, stop], ids=["error", "stop"])
def test_the_disclaimer_survives_a_page_that_fails_or_stops(
    monkeypatch: pytest.MonkeyPatch, check_sources: Callable[..., None]
) -> None:
    monkeypatch.setattr(diagnostics, "check_sources", check_sources)
    app = run_app(DATA_SOURCES_PAGE)
    button(app, data_sources.CHECK_BUTTON).click().run()

    assert DISCLAIMER in captions(app)


def stress_test_page(monkeypatch: pytest.MonkeyPatch, library: FakeLibrary) -> AppTest:
    """The Stress-test page, with share prices served by a fake library."""
    monkeypatch.setattr(client, "make_client", library.client)
    return run_app(STRESS_TEST_PAGE)


def design_page_with_a_problem() -> AppTest:
    """The Design page with one split that does not add up, so every message shows."""
    app = run_app(DESIGN_PAGE)
    app.number_input(key=percent_key(1, "ftse_gilts_all_stocks")).set_value(45).run()
    app.toggle(key=widget_key(3, "included")).set_value(False).run()
    return app


def column(app: AppTest, heading: str) -> dict[str, str]:
    """One column of the Stress-test table, keyed by split."""
    table = app.table[0].value
    return dict(zip(table["Split"], table[heading], strict=True))


EXAMPLE_NAMES = [split.name for split in EXAMPLE_SPLITS]


def test_the_stress_test_shows_every_example_through_a_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = stress_test_page(monkeypatch, FakeLibrary())

    assert [subheader.value for subheader in app.subheader][: len(EXAMPLE_NAMES)] == EXAMPLE_NAMES
    assert list(column(app, "Worst fall in the crash")) == EXAMPLE_NAMES
    assert "No data" not in column(app, "Worst fall in the crash").values()
    assert len(app.get("vega_lite_chart")) == 1
    assert not app.warning
    assert DISCLAIMER in captions(app)


def test_choosing_another_crash_tells_its_story(monkeypatch: pytest.MonkeyPatch) -> None:
    app = stress_test_page(monkeypatch, FakeLibrary())
    button_group(app, state.CRASH).set_value(COVID.key).run()

    assert stress_test.EPISODE_STORIES[COVID.key] in [markdown.value for markdown in app.markdown]


def test_without_share_prices_bonds_and_cash_still_have_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = stress_test_page(monkeypatch, FakeLibrary(online=False))

    assert app.warning[0].value == stress_test.offline_banner(["ftse_all_world"])
    falls = column(app, "Worst fall in the crash")
    assert [name for name, fall in falls.items() if fall != "No data"] == ["Cash only"]
    assert len(app.get("vega_lite_chart")) == 1


def test_try_again_fetches_share_prices_once_the_library_is_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    library = FakeLibrary(online=False)
    app = stress_test_page(monkeypatch, library)
    library.online = True

    assert app.run().warning, "a recent failure is not retried on its own"
    button(app, stress_test.TRY_AGAIN).click().run()

    assert not app.warning
    assert "No data" not in column(app, "Worst fall in the crash").values()


RENDERED_PAGES: dict[str, Callable[[pytest.MonkeyPatch], AppTest]] = {
    "home": lambda _monkeypatch: run_app(),
    "data sources": checked_data_sources_page,
    "stress test": lambda monkeypatch: stress_test_page(monkeypatch, FakeLibrary()),
    "stress test offline": lambda monkeypatch: stress_test_page(
        monkeypatch, FakeLibrary(online=False)
    ),
    "design": lambda _monkeypatch: run_app(DESIGN_PAGE),
    "design with a problem": lambda _monkeypatch: design_page_with_a_problem(),
}


@pytest.mark.parametrize("page", RENDERED_PAGES)
def test_every_rendered_word_follows_the_copy_rules(
    monkeypatch: pytest.MonkeyPatch, page: str
) -> None:
    texts = rendered_text(RENDERED_PAGES[page](monkeypatch))

    assert texts
    assert {text: copy_problems(text) for text in texts if copy_problems(text)} == {}


@pytest.mark.parametrize("page", PAGES, ids=lambda page: page.stem)
def test_pages_hold_no_bare_strings_that_streamlit_would_draw(page: Path) -> None:
    module = ast.parse(page.read_text(encoding="utf-8"))
    docstring = module.body[0]
    bare_strings = [
        node.lineno
        for node in ast.walk(module)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        and node is not docstring
    ]
    assert bare_strings == []


def page_links(app: AppTest) -> dict[str, str]:
    return {link.proto.label: link.proto.page for link in app.get("page_link")}


def test_the_footer_links_to_the_source_code_when_the_repository_is_declared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(footer, "repository_url", lambda: "https://github.com/example/repo")

    assert page_links(run_app())[SOURCE_CODE] == "https://github.com/example/repo"


def test_the_footer_leaves_out_the_source_link_when_no_repository_is_declared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(footer, "repository_url", lambda: None)

    assert SOURCE_CODE not in page_links(run_app())
