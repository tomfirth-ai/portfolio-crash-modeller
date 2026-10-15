"""Design: up to four splits of money between the building blocks, side by side."""

from itertools import batched

import streamlit as st

from crashmodel.app import navigation, state
from crashmodel.app.presenters import design as presenter
from crashmodel.app.presenters.blocks import BLOCK_DEFINITIONS
from crashmodel.app.splits import WHOLE
from crashmodel.data.blocks import Block

# Two cards a row keep each box wide enough for its label.
CARDS_PER_ROW = 2

session = st.session_state

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
            for block in Block:
                st.number_input(
                    presenter.block_label(block),
                    min_value=0,
                    max_value=WHOLE,
                    step=presenter.PERCENT_STEP,
                    help=BLOCK_DEFINITIONS[block],
                    key=state.widget_key(index, block),
                    disabled=left_out,
                    on_change=state.commit,
                    args=(session, index),
                )
            badge = presenter.total_badge(slot)
            st.badge(badge.text, icon=badge.icon, color=badge.colour)

blocker = presenter.next_blocker(slots)
if st.button(
    presenter.NEXT, type="primary", icon=":material/arrow_forward:", disabled=blocker is not None
):
    st.switch_page(navigation.stress_test_page())
if blocker is not None:
    st.caption(blocker)
