"""The footer drawn under every page."""

import streamlit as st

from crashmodel.app.presenters.copy import DISCLAIMER, NOT_AFFILIATED, SOURCE_CODE, TRADE_MARKS
from crashmodel.project import repository_url


def render_footer(data_sources_page: st.Page) -> None:
    """Draw the disclaimer and the notices about names, then links to the data and the code."""
    st.divider()
    st.caption(DISCLAIMER)
    st.caption(f"{NOT_AFFILIATED} {TRADE_MARKS}")
    with st.container(horizontal=True):
        st.page_link(data_sources_page)
        if (url := repository_url()) is not None:
            st.page_link(url, label=SOURCE_CODE, icon=":material/code:")
