from typing import Any

import pytest

from crashmodel.app import state
from crashmodel.app.splits import (
    BALANCED,
    CAUTIOUS,
    EXAMPLE_SPLITS,
    Slot,
    Split,
    empty_slots,
    example_slots,
)
from crashmodel.app.state import INCLUDED, NAME, TEMPLATE, SessionState, widget_key
from crashmodel.data.blocks import Block


def started() -> SessionState:
    session: dict[str | int, Any] = {}
    state.ensure_started(session)
    state.load_widgets(session)
    return session


def test_a_new_session_starts_with_the_examples() -> None:
    assert state.slots(started()) == example_slots()


def test_starting_again_keeps_the_visitors_splits() -> None:
    session = started()
    state.start_own(session)
    state.ensure_started(session)
    assert state.slots(session) == empty_slots()


def test_widgets_show_each_slot_and_write_their_changes_back() -> None:
    session = started()
    assert session[widget_key(1, NAME)] == "Balanced"
    assert session[widget_key(1, Block.US_SHARES)] == 0

    session[widget_key(1, NAME)] = "Mine"
    session[widget_key(1, Block.UK_BONDS)] = 45
    session[widget_key(1, INCLUDED)] = False
    state.commit(session, 1)

    mine = Split(name="Mine", percentages={Block.GLOBAL_SHARES: 60, Block.UK_BONDS: 45})
    assert state.slots(session)[1] == Slot(split=mine, included=False)
    assert state.slots(session)[0] == example_slots()[0]


def test_writing_back_unchanged_widgets_leaves_the_examples_as_they_were() -> None:
    session = started()
    for index in range(len(EXAMPLE_SPLITS)):
        state.commit(session, index)
    assert state.slots(session) == example_slots()


def test_choosing_an_example_fills_the_slot_and_clears_the_menu() -> None:
    session = started()
    state.start_own(session)
    session[widget_key(2, TEMPLATE)] = CAUTIOUS.name
    state.use_template(session, 2)

    assert state.slots(session)[2] == Slot(split=CAUTIOUS)
    assert session[widget_key(2, TEMPLATE)] is None


def test_starting_your_own_and_going_back_to_the_examples() -> None:
    session = started()
    state.start_own(session)
    assert [slot.included for slot in state.slots(session)] == [True, False, False, False]
    assert all(slot.split.total == 0 for slot in state.slots(session))

    state.show_examples(session)
    assert state.slots(session) == example_slots()


def test_a_split_cannot_be_changed_once_made() -> None:
    percentages: Any = state.slots(started())[1].split.percentages
    with pytest.raises(TypeError):
        percentages[Block.CASH] = 50
    assert BALANCED.total == 100
