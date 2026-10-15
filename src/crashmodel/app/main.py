"""Build the app: page configuration, navigation and the footer shared by every page."""

import streamlit as st

from crashmodel.app import navigation
from crashmodel.app.components.footer import render_footer
from crashmodel.app.presenters.copy import JOURNEY_SECTION, REFERENCE_SECTION, page_title


def main() -> None:
    """Configure the app, then run the selected page above the shared footer.

    The footer, and with it the disclaimer, is drawn before the page runs, into the space below
    the page. It therefore shows even when a page raises an error or stops early with ``st.stop``.
    """
    # The cards and tables are laid out for the centred column, whatever the screen width.
    st.set_page_config(page_icon=":material/thunderstorm:", layout="centered")
    sources = navigation.data_sources_page()
    page = st.navigation(
        {
            "": [navigation.home_page()],
            JOURNEY_SECTION: [navigation.stress_test_page()],
            REFERENCE_SECTION: [sources],
        }
    )
    # Set after navigation: a title set earlier would replace every page's own tab title.
    st.set_page_config(page_title=page_title(page.title))
    body = st.container()
    render_footer(sources)
    with body:
        page.run()
