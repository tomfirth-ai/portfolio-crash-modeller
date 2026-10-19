from typing import Any

import pytest

from crashmodel.app import state
from crashmodel.app.splits import (
    EXAMPLE_SPLITS,
    MOST_SLOTS,
    MOSTLY_BONDS,
    SHARES_AND_BONDS,
    Slot,
    Split,
    empty_slots,
    example_slots,
)
from crashmodel.app.state import (
    HOLDINGS,
    INCLUDED,
    NAME,
    SLOTS,
    TEMPLATE,
    SessionState,
    percent_key,
    widget_key,
)


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
    assert session[widget_key(1, NAME)] == "Shares and bonds"
    assert session[widget_key(1, HOLDINGS)] == ["ftse_all_world", "ftse_gilts_all_stocks"]
    assert session[percent_key(1, "ftse_gilts_all_stocks")] == 40

    session[widget_key(1, NAME)] = "Mine"
    session[widget_key(1, INCLUDED)] = False
    state.commit(session, 1)
    session[percent_key(1, "ftse_gilts_all_stocks")] = 45
    state.set_percent(session, 1, "ftse_gilts_all_stocks")

    mine = Split(name="Mine", percentages={"ftse_all_world": 60, "ftse_gilts_all_stocks": 45})
    assert state.slots(session)[1] == Slot(split=mine, included=False)
    assert state.slots(session)[0] == example_slots()[0]


def choose(session: SessionState, index: int, holdings: list[str]) -> dict[str, int]:
    session[widget_key(index, HOLDINGS)] = holdings
    state.choose_holdings(session, index)
    return dict(state.slots(session)[index].split.percentages)


def test_a_new_holding_gets_whatever_brings_the_split_up_to_100() -> None:
    session = started()
    state.start_own(session)
    assert choose(session, 0, ["sp500"]) == {"sp500": 100}
    assert choose(session, 0, ["sp500", "sonia"]) == {"sp500": 100, "sonia": 0}

    session[percent_key(0, "sp500")] = 70
    state.set_percent(session, 0, "sp500")
    assert choose(session, 0, ["sp500", "sonia", "ftse_gilts_all_stocks"]) == {
        "sp500": 70,
        "sonia": 0,
        "ftse_gilts_all_stocks": 30,
    }


def test_removing_a_holding_keeps_the_others_and_their_order() -> None:
    session = started()
    assert choose(session, 0, ["sonia", "ftse_all_world"]) == {
        "sonia": 20,
        "ftse_all_world": 20,
    }
    assert list(state.slots(session)[0].split.percentages) == ["sonia", "ftse_all_world"]


def test_a_session_keeps_its_splits_when_a_holding_leaves_the_catalogue() -> None:
    session = started()
    kept = Split(name="Mine", percentages={"sp500": 60, "withdrawn": 40})
    session[SLOTS] = (Slot(split=kept), *example_slots()[1:])
    state.ensure_started(session)
    assert state.slots(session)[0].split.percentages == {"sp500": 60}
    assert state.slots(session)[1:] == example_slots()[1:]


def test_writing_back_unchanged_widgets_leaves_the_examples_as_they_were() -> None:
    session = started()
    for index in range(len(EXAMPLE_SPLITS)):
        state.commit(session, index)
    assert state.slots(session) == example_slots()


def test_choosing_an_example_fills_the_slot_and_clears_the_menu() -> None:
    session = started()
    state.start_own(session)
    session[widget_key(2, TEMPLATE)] = MOSTLY_BONDS.name
    state.use_template(session, 2)

    assert state.slots(session)[2] == Slot(split=MOSTLY_BONDS)
    assert session[widget_key(2, TEMPLATE)] is None


def test_starting_your_own_and_going_back_to_the_examples() -> None:
    session = started()
    state.start_own(session)
    assert [slot.included for slot in state.slots(session)] == [True, False, False, False]
    assert all(slot.split.total == 0 for slot in state.slots(session))

    state.show_examples(session)
    assert state.slots(session) == example_slots()


def test_splits_are_added_after_the_examples_up_to_six() -> None:
    session = started()
    for _ in range(MOST_SLOTS):
        state.add_split(session)

    added = state.slots(session)[len(EXAMPLE_SPLITS) :]
    assert len(state.slots(session)) == MOST_SLOTS
    assert [slot.split.name for slot in added] == ["Split 5", "Split 6"]
    assert all(slot.included and slot.split.total == 0 for slot in added)

    state.show_examples(session)
    assert state.slots(session) == example_slots()


def test_a_split_cannot_be_changed_once_made() -> None:
    percentages: Any = state.slots(started())[1].split.percentages
    with pytest.raises(TypeError):
        percentages["sonia"] = 50
    assert SHARES_AND_BONDS.total == 100
