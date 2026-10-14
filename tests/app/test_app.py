"""Smoke tests that run the real Streamlit app in-process, with the network blocked."""

import ast
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from crashmodel.app.components import footer
from crashmodel.app.presenters.copy import DISCLAIMER, SOURCE_CODE
from crashmodel.data import diagnostics
from tests.app.copy_rules import copy_problems

ENTRY_POINT = Path(__file__).parents[2] / "streamlit_app.py"
PAGES = sorted((Path(__file__).parents[2] / "src/crashmodel/app/pages").glob("[!_]*.py"))
DATA_SOURCES_PAGE = "src/crashmodel/app/pages/data_sources.py"
RUN_TIMEOUT_SECONDS = 30
"""Generous, because the first run imports the dataframe stack."""


def run_app() -> AppTest:
    app = AppTest.from_file(ENTRY_POINT, default_timeout=RUN_TIMEOUT_SECONDS).run()
    assert not app.exception
    return app


def captions(app: AppTest) -> list[str]:
    return [caption.value for caption in app.caption]


def test_home_explains_the_journey() -> None:
    app = run_app()

    assert app.title[0].value == "How would your investments have coped with a crash?"
    steps = [subheader.value for subheader in app.subheader]
    assert steps == ["Design", "Stress-test", "Decide", "Track"]


def test_home_shows_the_disclaimer() -> None:
    assert DISCLAIMER in captions(run_app())


def offline_client() -> httpx.Client:
    def refuse(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network blocked in tests")

    return httpx.Client(transport=httpx.MockTransport(refuse))


def checked_data_sources_page(monkeypatch: pytest.MonkeyPatch) -> AppTest:
    """The Data sources page after its check has run, with the network refused."""
    monkeypatch.setattr(diagnostics, "make_client", offline_client)
    app = run_app().switch_page(DATA_SOURCES_PAGE).run()
    return app.button[0].click().run()


def rendered_text(app: AppTest) -> list[str]:
    """Every piece of text the page shows: headings, prose, buttons, links and table cells."""
    kinds = ("title", "header", "subheader", "markdown", "caption", "info", "warning", "error")
    texts = [element.value for kind in kinds for element in getattr(app, kind)]
    texts += [button.label for button in app.button]
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
    assert list(app.table[0].value["Status"]) == ["Unreachable: could not connect"] * sources
    assert DISCLAIMER in captions(app)


def fail(*_args: object) -> None:
    raise RuntimeError("a page bug")


def stop(*_args: object) -> None:
    st.stop()


@pytest.mark.parametrize("check_sources", [fail, stop], ids=["error", "stop"])
def test_the_disclaimer_survives_a_page_that_fails_or_stops(
    monkeypatch: pytest.MonkeyPatch, check_sources: Callable[..., None]
) -> None:
    monkeypatch.setattr(diagnostics, "check_sources", check_sources)
    app = run_app().switch_page(DATA_SOURCES_PAGE).run()
    app.button[0].click().run()

    assert DISCLAIMER in captions(app)


@pytest.mark.parametrize("page", ["home", "data sources"])
def test_every_rendered_word_follows_the_copy_rules(
    monkeypatch: pytest.MonkeyPatch, page: str
) -> None:
    app = run_app() if page == "home" else checked_data_sources_page(monkeypatch)
    texts = rendered_text(app)

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
