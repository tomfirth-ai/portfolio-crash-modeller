"""Stress-test: how each split came through a real crash, in words, figures and a chart."""

from itertools import batched

import streamlit as st

from crashmodel.app import loaders, navigation, state
from crashmodel.app.charts import value_chart
from crashmodel.app.presenters import stress_test as presenter
from crashmodel.engine.episodes import EPISODES, EPISODES_BY_KEY

# Two cards a row leave room for each story.
CARDS_PER_ROW = 2

slots = state.slots(st.session_state)

st.title(presenter.TITLE)
st.write(presenter.INTRODUCTION)
if note := presenter.examples_note(slots):
    st.caption(note)
st.page_link(navigation.design_page(), label=presenter.CHANGE_SPLITS, icon=":material/edit:")
if note := presenter.left_out_note(slots):
    st.warning(note, icon=":material/rule:")

# Keys rather than episodes are the options, because Streamlit reads a dataclass as a mapping.
key = st.segmented_control(
    presenter.CRASH_PICKER,
    list(EPISODES_BY_KEY),
    default=EPISODES[0].key,
    required=True,
    format_func=presenter.episode_name,
)
episode = EPISODES_BY_KEY[key]
st.write(presenter.EPISODE_STORIES[episode.key])

with st.spinner(presenter.FETCHING):
    panel = loaders.load_panel()
if panel.unavailable:
    st.warning(presenter.OFFLINE_BANNER, icon=":material/cloud_off:")
    st.button(presenter.TRY_AGAIN, icon=":material/refresh:", on_click=loaders.try_again)

results = presenter.outcomes(slots, episode, panel)
if not results:
    st.info(presenter.NO_SPLITS, icon=":material/info:")
    st.stop()
for row in batched(results, CARDS_PER_ROW):
    for column, outcome in zip(st.columns(CARDS_PER_ROW, border=True), row, strict=False):
        card = presenter.card(outcome, episode)
        with column:
            st.subheader(card.title, anchor=False)
            st.write(card.text)

st.subheader(presenter.TABLE_HEADING, anchor=False)
st.table([presenter.table_row(outcome, episode) for outcome in results], hide_index=True)

chart = presenter.chart_view(results)
if chart.points:
    st.subheader(presenter.CHART_HEADING, anchor=False)
    st.altair_chart(value_chart(chart), width="stretch")

st.subheader(presenter.DATA_HEADING, anchor=False)
st.caption(presenter.CAVEAT)
st.caption(presenter.BANK_OF_ENGLAND_CREDIT)
st.caption(presenter.share_credit(panel.vintages))
