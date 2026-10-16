"""Stress-test: how each split came through a real crash, in words, figures and a chart."""

from itertools import batched

import streamlit as st

from crashmodel.app import loaders, navigation, state, stress
from crashmodel.app.charts import value_chart
from crashmodel.app.journey import STRESS_TEST
from crashmodel.app.presenters import stress_test as presenter
from crashmodel.app.presenters.progress import progress
from crashmodel.engine.episodes import EPISODES_BY_KEY, GLOBAL_FINANCIAL_CRISIS
from crashmodel.engine.portfolio import Rebalancing

# Two cards a row leave room for each story.
CARDS_PER_ROW = 2

slots = state.slots(st.session_state)

step = progress(STRESS_TEST)
st.progress(step.fraction, text=step.text)
st.title(presenter.TITLE)
st.write(presenter.INTRODUCTION)
if note := presenter.examples_note(slots):
    st.caption(note)
st.page_link(navigation.design_page(), label=presenter.CHANGE_SPLITS, icon=":material/edit:")
if note := presenter.left_out_note(slots):
    st.warning(note, icon=":material/rule:")

# Strings are the options, because Streamlit reads a dataclass as a mapping. Both choices are kept
# for the session, so they survive a visit to another page.
with st.container(horizontal=True):
    key = st.segmented_control(
        presenter.CRASH_PICKER,
        list(EPISODES_BY_KEY),
        default=GLOBAL_FINANCIAL_CRISIS.key,
        required=True,
        format_func=presenter.episode_name,
        key=state.CRASH,
        persist_state="session",
        wrap=True,
    )
    management = st.segmented_control(
        presenter.MANAGEMENT_PICKER,
        list(presenter.MANAGEMENT_NAMES),
        default=Rebalancing.MONTHLY.value,
        required=True,
        format_func=presenter.management_name,
        help=presenter.MANAGEMENT_HELP,
        key=state.MANAGEMENT,
        persist_state="session",
        wrap=True,
    )
episode = EPISODES_BY_KEY[key]
st.write(presenter.EPISODE_STORIES[episode.key])

with st.spinner(presenter.FETCHING):
    panel = loaders.load_panel(stress.models_held(slots))
if unavailable := stress.unavailable_holdings(slots, panel):
    st.warning(presenter.offline_banner(unavailable), icon=":material/cloud_off:")
    st.button(presenter.TRY_AGAIN, icon=":material/refresh:", on_click=loaders.try_again)

results = stress.outcomes(slots, episode, panel, Rebalancing(management))
if not results:
    st.info(presenter.NO_SPLITS, icon=":material/info:")
    st.stop()
for row in batched(results, CARDS_PER_ROW):
    # Borders go on the cards, not the columns, so a row with one card shows no empty box.
    for column, outcome in zip(st.columns(CARDS_PER_ROW), row, strict=False):
        card = presenter.card(outcome, episode)
        with column, st.container(border=True, height="stretch"):
            st.subheader(card.title, anchor=False)
            st.write(card.text)
            if card.why:
                st.write(card.why_text)
            if card.notes:
                st.caption(card.notes_text)

st.subheader(presenter.TABLE_HEADING, anchor=False)
st.table([presenter.table_row(outcome, episode) for outcome in results], hide_index=True)

chart = presenter.chart_view(results)
if chart.points:
    st.subheader(presenter.CHART_HEADING, anchor=False)
    st.caption(presenter.SIMULATED)
    st.altair_chart(value_chart(chart), width="stretch")

st.subheader(presenter.DATA_HEADING, anchor=False)
st.caption(presenter.CAVEAT)
st.caption(presenter.BANK_OF_ENGLAND_CREDIT)
st.caption(presenter.share_credit(panel.vintages))
