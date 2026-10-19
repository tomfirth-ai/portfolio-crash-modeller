"""How it works: the method in plain words, what it leaves out, and the project behind it."""

import streamlit as st

from crashmodel.app.presenters import how_it_works as presenter
from crashmodel.project import repository_url

st.title(presenter.TITLE)
st.write(presenter.INTRODUCTION)
for section in presenter.sections(repository_url()):
    st.subheader(section.heading, anchor=False)
    for paragraph in section.paragraphs:
        st.write(paragraph)
