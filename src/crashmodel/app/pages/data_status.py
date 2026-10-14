"""Data status: can the app reach the sources it fetches at runtime?"""

import streamlit as st

from crashmodel.app.presenters import data_status as presenter
from crashmodel.data import diagnostics

st.title(presenter.TITLE)
st.write(presenter.INTRODUCTION)

if st.button("Run check", type="primary", icon=":material/network_check:"):
    with st.spinner("Checking each source..."), diagnostics.make_client() as client:
        results = diagnostics.check_sources(client, diagnostics.HOSTED_SOURCES)
    st.write(presenter.summary(results))
    st.dataframe(presenter.status_table(results), hide_index=True)
