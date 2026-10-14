"""The footer drawn under every page."""

import streamlit as st

from crashmodel.app.presenters.copy import DISCLAIMER


def render_footer(data_sources_page: st.Page) -> None:
    """Draw the disclaimer and a link to the data sources page, labelled with its title."""
    st.divider()
    st.caption(DISCLAIMER)
    st.page_link(data_sources_page)
