"""Data sources: what is stored with the app, what it fetches, and whether that can be reached."""

import streamlit as st

from crashmodel.app import loaders
from crashmodel.app.presenters import data_sources as presenter

st.title(presenter.TITLE)
st.write(presenter.INTRODUCTION)

st.subheader(presenter.STORED_HEADING, anchor=False)
st.write(presenter.STORED_INTRODUCTION)
st.table(presenter.stored_table(), hide_index=True)
st.caption(presenter.BOND_METHOD)

st.subheader(presenter.FETCHED_HEADING, anchor=False)
st.write(presenter.FETCHED_INTRODUCTION)
if st.button(presenter.CHECK_BUTTON, type="primary", icon=":material/network_check:"):
    with st.spinner(presenter.CHECKING):
        results = loaders.source_checks()
    st.write(presenter.summary(results))
    st.table(presenter.status_table(results), hide_index=True)
