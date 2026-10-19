"""Home: the question the tool answers, the first step to take, and the four-step journey."""

from itertools import batched

import streamlit as st

from crashmodel.app import navigation
from crashmodel.app.journey import DESIGN, STRESS_TEST
from crashmodel.app.presenters.home import home_view

# Two cards a row leave room for each summary; four in a row squeeze the titles.
CARDS_PER_ROW = 2

view = home_view()

st.caption(view.eyebrow)
st.title(view.headline)
st.write(view.promise)
with st.container(horizontal=True):
    if st.button(view.first_step, type="primary", icon=STRESS_TEST.icon):
        st.switch_page(navigation.stress_test_page())
    if st.button(view.second_step, icon=DESIGN.icon):
        st.switch_page(navigation.design_page())
st.info(view.status_note, icon=":material/construction:")

for row in batched(view.steps, CARDS_PER_ROW):
    for column, card in zip(st.columns(CARDS_PER_ROW, border=True), row, strict=False):
        with column:
            st.caption(card.label)
            st.subheader(card.title, icon=card.icon, anchor=False)
            if card.badge is None:
                st.write(card.summary)
            else:
                st.badge(card.badge, icon=":material/schedule:", color="gray")
                st.caption(card.summary)
