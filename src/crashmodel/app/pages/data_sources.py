"""Data sources: where runtime data comes from, and whether each source can be reached."""

import streamlit as st

from crashmodel.app.presenters import data_sources as presenter
from crashmodel.data import client, diagnostics

st.title(presenter.TITLE)
st.write(presenter.INTRODUCTION)

if st.button(presenter.CHECK_BUTTON, type="primary", icon=":material/network_check:"):
    with st.spinner(presenter.CHECKING), client.make_client() as http_client:
        results = diagnostics.check_sources(http_client, diagnostics.HOSTED_SOURCES)
    st.write(presenter.summary(results))
    st.table(presenter.status_table(results), hide_index=True)
