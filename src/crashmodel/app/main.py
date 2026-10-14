"""Build the app: page configuration, navigation and the footer shared by every page."""

from pathlib import Path

import streamlit as st

from crashmodel.app.components.footer import render_footer
from crashmodel.app.presenters.copy import APP_NAME

PAGES_DIRECTORY = Path(__file__).parent / "pages"


def main() -> None:
    """Configure the app, then run the selected page above the shared footer.

    The footer, and with it the disclaimer, is drawn before the page runs, into the space below
    the page. It therefore shows even when a page raises an error or stops early with ``st.stop``.
    """
    st.set_page_config(page_title=APP_NAME, page_icon=":material/thunderstorm:", layout="centered")
    home = st.Page(PAGES_DIRECTORY / "home.py", title="Home", icon=":material/home:", default=True)
    data_status = st.Page(
        PAGES_DIRECTORY / "data_status.py",
        title="Data status",
        icon=":material/database:",
        url_path="data-status",
    )
    page = st.navigation(
        {"": [home], "Reference": [data_status]}, position="sidebar", expanded=True
    )
    body = st.container()
    render_footer(data_status)
    with body:
        page.run()
