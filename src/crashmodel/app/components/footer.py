"""The footer drawn under every page."""

import streamlit as st

from crashmodel.app.presenters.copy import DISCLAIMER, SOURCE_CODE
from crashmodel.project import repository_url


def render_footer(data_sources_page: st.Page) -> None:
    """Draw the disclaimer, then links to the data sources page and to the source code."""
    st.divider()
    st.caption(DISCLAIMER)
    with st.container(horizontal=True):
        st.page_link(data_sources_page)
        if (url := repository_url()) is not None:
            st.page_link(url, label=SOURCE_CODE, icon=":material/code:")
