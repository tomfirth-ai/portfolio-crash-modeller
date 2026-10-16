"""Design: up to four splits of money between funds and indexes, side by side."""

from itertools import batched

import streamlit as st

from crashmodel.app import navigation, state
from crashmodel.app.charts import composition_chart
from crashmodel.app.journey import DESIGN
from crashmodel.app.presenters import design as presenter
from crashmodel.app.presenters.holdings import holding_help, holding_label
from crashmodel.app.presenters.progress import progress
from crashmodel.app.splits import WHOLE
from crashmodel.data.catalogue import HOLDINGS_BY_ID

# Two cards a row keep each box wide enough for its label.
CARDS_PER_ROW = 2

session = st.session_state

step = progress(DESIGN)
st.progress(step.fraction, text=step.text)
st.title(presenter.TITLE)
st.write(presenter.INTRODUCTION)
with st.container(horizontal=True):
    st.button(presenter.START_OWN, icon=":material/add:", on_click=state.start_own, args=(session,))
    st.button(
        presenter.SHOW_EXAMPLES,
        icon=":material/restart_alt:",
        on_click=state.show_examples,
        args=(session,),
    )

state.load_widgets(session)
slots = state.slots(session)
for row in batched(enumerate(slots), CARDS_PER_ROW):
    for column, (index, slot) in zip(st.columns(CARDS_PER_ROW, border=True), row, strict=False):
        with column:
            left_out = not slot.included
            st.toggle(
                presenter.INCLUDE,
                key=state.widget_key(index, state.INCLUDED),
                on_change=state.commit,
                args=(session, index),
            )
            st.text_input(
                presenter.NAME,
                key=state.widget_key(index, state.NAME),
                max_chars=presenter.NAME_MAX_CHARACTERS,
                disabled=left_out,
                on_change=state.commit,
                args=(session, index),
            )
            st.selectbox(
                presenter.TEMPLATE,
                presenter.TEMPLATE_NAMES,
                index=None,
                placeholder=presenter.TEMPLATE_PLACEHOLDER,
                key=state.widget_key(index, state.TEMPLATE),
                disabled=left_out,
                on_change=state.use_template,
                args=(session, index),
            )
            st.multiselect(
                presenter.HOLDINGS,
                list(HOLDINGS_BY_ID),
                format_func=holding_label,
                key=state.widget_key(index, state.HOLDINGS),
                help=presenter.HOLDINGS_HELP,
                max_selections=presenter.MAX_HOLDINGS,
                placeholder=presenter.HOLDINGS_PLACEHOLDER,
                select_all=False,
                wrap=True,
                disabled=left_out,
                on_change=state.choose_holdings,
                args=(session, index),
            )
            for holding in slot.split.percentages:
                st.number_input(
                    presenter.percent_label(holding),
                    min_value=0,
                    max_value=WHOLE,
                    step=presenter.PERCENT_STEP,
                    help=holding_help(holding),
                    key=state.percent_key(index, holding),
                    disabled=left_out,
                    on_change=state.set_percent,
                    args=(session, index, holding),
                )
            badge = presenter.total_badge(slot)
            st.badge(badge.text, icon=badge.icon, color=badge.colour)

composition = presenter.composition_view(slots)
if composition.points:
    st.subheader(presenter.COMPOSITION_HEADING, anchor=False)
    st.altair_chart(composition_chart(composition), width="stretch")

blocker = presenter.next_blocker(slots)
if st.button(
    presenter.NEXT, type="primary", icon=":material/arrow_forward:", disabled=blocker is not None
):
    st.switch_page(navigation.stress_test_page())
if blocker is not None:
    st.caption(blocker)
