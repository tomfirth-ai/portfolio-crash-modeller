"""Stress-test: how each split came through a real crash, in a chart, then in words and figures."""

from itertools import batched

import streamlit as st

from crashmodel.app import loaders, navigation, state, stress
from crashmodel.app.charts import value_chart
from crashmodel.app.journey import DESIGN, STRESS_TEST
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

notices = st.container()
# The crash picker and the chart share one panel, so the chart stays in place while the visitor
# flicks between crashes, and the stories follow below.
panel_box = st.container(border=True)
with panel_box, st.container(horizontal=True):
    # Strings are the options, because Streamlit reads a dataclass as a mapping. Both choices are
    # kept for the session, so they survive a visit to another page.
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
        key=state.MANAGEMENT,
        persist_state="session",
        wrap=True,
    )
episode = EPISODES_BY_KEY[key]

with panel_box, st.spinner(presenter.FETCHING):
    panel = loaders.load_panel(stress.models_held(slots))
if unavailable := stress.unavailable_holdings(slots, panel):
    with notices:
        st.warning(presenter.offline_banner(unavailable), icon=":material/cloud_off:")
        st.button(presenter.TRY_AGAIN, icon=":material/refresh:", on_click=loaders.try_again)

results = stress.outcomes(slots, episode, panel, Rebalancing(management))
if not results:
    with panel_box:
        st.info(presenter.NO_SPLITS, icon=":material/info:")
    st.stop()
chart = presenter.chart_view(results, episode)
if chart.points:
    with panel_box:
        st.altair_chart(value_chart(chart), width="stretch")
        # A caption rather than a tooltip, which a phone screen cuts off.
        st.caption(presenter.MANAGEMENT_HELP)
        st.caption(presenter.SIMULATED)

st.write(presenter.EPISODE_STORIES[episode.key])
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

st.subheader(presenter.DATA_HEADING, anchor=False)
st.caption(presenter.CAVEAT)
st.caption(presenter.BANK_OF_ENGLAND_CREDIT)
st.caption(presenter.share_credit(panel.vintages))

with st.container(border=True):
    st.subheader(presenter.NEXT_HEADING, anchor=False)
    st.write(presenter.NEXT_TEXT)
    with st.container(horizontal=True):
        st.page_link(navigation.design_page(), label=presenter.DESIGN_OWN, icon=DESIGN.icon)
        st.page_link(navigation.how_it_works_page(), label=presenter.HOW_IT_WORKS)
