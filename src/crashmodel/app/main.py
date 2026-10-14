"""Build the app: page configuration, navigation and the footer shared by every page."""

from pathlib import Path

import streamlit as st

from crashmodel.app.components.footer import render_footer
from crashmodel.app.presenters import data_sources
from crashmodel.app.presenters.copy import HOME_TITLE, REFERENCE_SECTION, page_title

PAGES_DIRECTORY = Path(__file__).parent / "pages"


def main() -> None:
    """Configure the app, then run the selected page above the shared footer.

    The footer, and with it the disclaimer, is drawn before the page runs, into the space below
    the page. It therefore shows even when a page raises an error or stops early with ``st.stop``.
    """
    # The cards and tables are laid out for the centred column, whatever the screen width.
    st.set_page_config(page_icon=":material/thunderstorm:", layout="centered")
    home = st.Page(
        PAGES_DIRECTORY / "home.py", title=HOME_TITLE, icon=":material/home:", default=True
    )
    sources = st.Page(
        PAGES_DIRECTORY / "data_sources.py",
        title=data_sources.TITLE,
        icon=":material/database:",
        url_path="data-sources",
    )
    page = st.navigation({"": [home], REFERENCE_SECTION: [sources]})
    # Set after navigation: a title set earlier would replace every page's own tab title.
    st.set_page_config(page_title=page_title(page.title))
    body = st.container()
    render_footer(sources)
    with body:
        page.run()
