"""Running the real app in-process for tests, and finding things on its pages."""

from pathlib import Path

from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import Button, ButtonGroup

ROOT = Path(__file__).parents[2]
ENTRY_POINT = ROOT / "streamlit_app.py"
PAGES = sorted((ROOT / "src/crashmodel/app/pages").glob("[!_]*.py"))
DESIGN_PAGE = "src/crashmodel/app/pages/design.py"
STRESS_TEST_PAGE = "src/crashmodel/app/pages/stress_test.py"
DATA_SOURCES_PAGE = "src/crashmodel/app/pages/data_sources.py"
RUN_TIMEOUT_SECONDS = 30
"""Generous, because the first run imports the dataframe stack."""


def run_app(page: str | None = None) -> AppTest:
    """Start a new session, as a new visitor would, optionally opening a page by its path."""
    app = AppTest.from_file(ENTRY_POINT, default_timeout=RUN_TIMEOUT_SECONDS).run()
    if page is not None:
        app.switch_page(page).run()
    assert not app.exception
    return app


def button(app: AppTest, label: str) -> Button:
    """The button with this label."""
    [match] = [candidate for candidate in app.button if candidate.label == label]
    return match


def click(app: AppTest, label: str) -> AppTest:
    """Click the button with this label and run the app again."""
    button(app, label).click().run()
    assert not app.exception
    return app


def captions(app: AppTest) -> list[str]:
    return [caption.value for caption in app.caption]


def button_groups(app: AppTest) -> list[ButtonGroup[str]]:
    """The segmented controls on the page."""
    return [group for group in app.get("button_group") if isinstance(group, ButtonGroup)]


def click_through(app: AppTest, label: str, page: str) -> AppTest:
    """Click a button that opens another page, and stay on that page for the next run.

    AppTest shows the page a button switches to, but its next run goes back to the page it was
    on, so the test follows the switch itself.
    """
    click(app, label)
    return app.switch_page(page)
