"""Home: the question the tool answers, and the four-step journey."""

import streamlit as st

from crashmodel.app.presenters.home import home_view

view = home_view()

st.caption(view.eyebrow)
st.title(view.headline)
st.write(view.promise)

for column, card in zip(st.columns(len(view.steps)), view.steps, strict=True):
    with column.container(border=True):
        st.caption(card.label)
        st.markdown(f"{card.icon} **{card.title}**")
        st.write(card.summary)

st.caption(view.status_note)
