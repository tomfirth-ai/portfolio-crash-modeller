"""Build the app: page configuration, navigation and the footer shared by every page."""

from pathlib import Path

import streamlit as st

from crashmodel.app.components.footer import render_footer
from crashmodel.app.presenters.copy import page_title

PAGES_DIRECTORY = Path(__file__).parent / "pages"


def main() -> None:
    """Configure the app, then run the selected page above the shared footer.

    The footer, and with it the disclaimer, is drawn before the page runs, into the space below
    the page. It therefore shows even when a page raises an error or stops early with ``st.stop``.
    """
    # The cards and tables are laid out for the centred column, whatever the screen width.
    st.set_page_config(page_icon=":material/thunderstorm:", layout="centered")
    home = st.Page(PAGES_DIRECTORY / "home.py", title="Home", icon=":material/home:", default=True)
    data_status = st.Page(
        PAGES_DIRECTORY / "data_status.py",
        title="Data status",
        icon=":material/database:",
        url_path="data-status",
    )
    page = st.navigation({"": [home], "Reference": [data_status]})
    # Set after navigation: a title set earlier would replace every page's own tab title.
    st.set_page_config(page_title=page_title(page.title))
    body = st.container()
    render_footer(data_status)
    with body:
        page.run()
