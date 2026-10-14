"""Smoke tests that run the real Streamlit app in-process, with the network blocked."""

from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from crashmodel.app.presenters.copy import DISCLAIMER
from crashmodel.data import diagnostics

ENTRY_POINT = Path(__file__).parents[2] / "streamlit_app.py"
DATA_STATUS_PAGE = "src/crashmodel/app/pages/data_status.py"
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
    page_text = " ".join(markdown.value for markdown in app.markdown)
    for step in ("Design", "Stress-test", "Decide", "Track"):
        assert step in page_text


def test_home_shows_the_disclaimer() -> None:
    assert DISCLAIMER in captions(run_app())


def test_data_status_reports_unreachable_sources_without_failing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def offline_client() -> httpx.Client:
        def refuse(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("network blocked in tests")

        return httpx.Client(transport=httpx.MockTransport(refuse))

    monkeypatch.setattr(diagnostics, "make_client", offline_client)
    app = run_app().switch_page(DATA_STATUS_PAGE).run()
    app.button[0].click().run()

    assert not app.exception
    assert "0 of 2 sources are reachable." in [markdown.value for markdown in app.markdown]
    statuses = list(app.dataframe[0].value["Status"])
    assert statuses == ["Unreachable (ConnectError)"] * 2
    assert DISCLAIMER in captions(app)
