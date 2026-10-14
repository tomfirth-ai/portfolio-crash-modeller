"""Home: the question the tool answers, and the four-step journey."""

from itertools import batched

import streamlit as st

from crashmodel.app.presenters.home import home_view

# Two cards a row leave room for each summary; four in a row squeeze the titles.
CARDS_PER_ROW = 2

view = home_view()

st.caption(view.eyebrow)
st.title(view.headline)
st.write(view.promise)
st.info(view.status_note, icon=":material/construction:")

for row in batched(view.steps, CARDS_PER_ROW):
    for column, card in zip(st.columns(CARDS_PER_ROW, border=True), row, strict=False):
        with column:
            st.caption(card.label)
            st.subheader(card.title, icon=card.icon, anchor=False)
            st.write(card.summary)
