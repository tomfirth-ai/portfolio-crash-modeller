"""The app's pages, defined in one place so that any page can link to any other.

Streamlit builds a page only while the app runs, so each is made by a function. Pages made from the
same definition are the same page, so a page can link to another by calling its function.
"""

from pathlib import Path

import streamlit as st

from crashmodel.app.journey import DESIGN, STRESS_TEST
from crashmodel.app.presenters import data_sources
from crashmodel.app.presenters.copy import HOME_TITLE

PAGES_DIRECTORY = Path(__file__).parent / "pages"


def home_page() -> st.Page:
    """The front page, which asks the question the tool answers."""
    return st.Page(
        PAGES_DIRECTORY / "home.py", title=HOME_TITLE, icon=":material/home:", default=True
    )


def design_page() -> st.Page:
    """The Design step."""
    return st.Page(
        PAGES_DIRECTORY / "design.py", title=DESIGN.title, icon=DESIGN.icon, url_path="design"
    )


def stress_test_page() -> st.Page:
    """The Stress-test step."""
    return st.Page(
        PAGES_DIRECTORY / "stress_test.py",
        title=STRESS_TEST.title,
        icon=STRESS_TEST.icon,
        url_path="stress-test",
    )


def data_sources_page() -> st.Page:
    """Where the data comes from, and whether the runtime sources can be reached."""
    return st.Page(
        PAGES_DIRECTORY / "data_sources.py",
        title=data_sources.TITLE,
        icon=":material/database:",
        url_path="data-sources",
    )
