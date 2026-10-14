"""The footer drawn under every page."""

import streamlit as st
from streamlit.navigation.page import StreamlitPage

from crashmodel.app.presenters.copy import DISCLAIMER


def render_footer(data_status_page: StreamlitPage) -> None:
    """Draw the disclaimer and a link to the data sources page."""
    st.divider()
    st.caption(DISCLAIMER)
    st.page_link(data_status_page, label="Data sources and status", icon=":material/database:")
