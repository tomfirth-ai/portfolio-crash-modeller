"""The visitor's four splits, kept in their session.

Streamlit forgets a widget's value once the visitor leaves its page. So each split is kept under a
session key that no widget uses: the Design page copies the splits into its widgets before drawing
them, and every widget writes its change back. The functions take the session state as a plain
mapping, so they are tested without Streamlit.
"""

from collections.abc import MutableMapping
from dataclasses import replace
from typing import Any

from crashmodel.app.splits import (
    EXAMPLE_SPLITS,
    WHOLE,
    Slot,
    empty_slots,
    example_slots,
)
from crashmodel.data.catalogue import HOLDINGS_BY_ID, HoldingId

type SessionState = MutableMapping[str | int, Any]

SLOTS = "splits"
"""The session key holding the four slots, which no widget uses. It changed when splits began to
hold funds, so a session open during that deploy starts again from the examples."""
CRASH = "crash"
"""The key of the Stress-test page's crash picker, which keeps its choice for the session."""
MANAGEMENT = "management"
"""The key of the Stress-test page's picker for how splits are managed."""
NAME = "name"
INCLUDED = "included"
TEMPLATE = "template"
HOLDINGS = "holdings"
TEMPLATES = {split.name: split for split in EXAMPLE_SPLITS}
"""The examples a slot can be filled from, by name."""


def ensure_started(state: SessionState) -> None:
    """Give a new session the examples, whichever page it opens first.

    A session that holds something no longer in the catalogue keeps the rest of its splits.
    """
    if SLOTS not in state:
        state[SLOTS] = example_slots()
    known = tuple(_known_holdings_only(slot) for slot in slots(state))
    if known != slots(state):
        state[SLOTS] = known


def slots(state: SessionState) -> tuple[Slot, ...]:
    """Return the session's four slots."""
    stored: tuple[Slot, ...] = state[SLOTS]
    return stored


def widget_key(index: int, field: str) -> str:
    """Return the session key of one of a slot's widgets, such as ``slot0.name``."""
    return f"slot{index}.{field}"


def percent_key(index: int, holding: HoldingId) -> str:
    """Return the session key of a slot's percentage box for one holding."""
    return widget_key(index, f"percent.{holding}")


def load_widgets(state: SessionState) -> None:
    """Copy each slot into its widgets' keys, so the widgets show it when drawn."""
    for index, slot in enumerate(slots(state)):
        state[widget_key(index, NAME)] = slot.split.name
        state[widget_key(index, INCLUDED)] = slot.included
        state[widget_key(index, HOLDINGS)] = list(slot.split.percentages)
        for holding, percent in slot.split.percentages.items():
            state[percent_key(index, holding)] = percent


def commit(state: SessionState, index: int) -> None:
    """Store a slot's name and whether it is included: the callback for those two widgets."""
    slot = slots(state)[index]
    split = replace(slot.split, name=state[widget_key(index, NAME)])
    _replace(state, index, Slot(split=split, included=state[widget_key(index, INCLUDED)]))


def choose_holdings(state: SessionState, index: int) -> None:
    """Store what a slot holds after the visitor adds or removes a holding.

    Holdings already there keep their percentages. A new one is given whatever brings the split up
    to 100, or nothing if it is already full, so the first holding added to an empty split starts
    at 100%.
    """
    slot = slots(state)[index]
    chosen: list[HoldingId] = state[widget_key(index, HOLDINGS)]
    current = slot.split.percentages
    kept = {holding: current[holding] for holding in chosen if holding in current}
    for holding in chosen:
        if holding not in kept:
            kept[holding] = max(0, WHOLE - sum(kept.values()))
    split = replace(slot.split, percentages={holding: kept[holding] for holding in chosen})
    _replace(state, index, replace(slot, split=split))


def set_percent(state: SessionState, index: int, holding: HoldingId) -> None:
    """Store a new percentage for one of a slot's holdings."""
    slot = slots(state)[index]
    percentages = {**slot.split.percentages, holding: state[percent_key(index, holding)]}
    _replace(state, index, replace(slot, split=replace(slot.split, percentages=percentages)))


def use_template(state: SessionState, index: int) -> None:
    """Fill a slot with the example chosen in its menu, then clear the menu."""
    _replace(state, index, Slot(split=TEMPLATES[state[widget_key(index, TEMPLATE)]]))
    state[widget_key(index, TEMPLATE)] = None


def show_examples(state: SessionState) -> None:
    """Put the examples back in all four slots."""
    state[SLOTS] = example_slots()


def start_own(state: SessionState) -> None:
    """Empty all four slots, so the visitor can start from scratch."""
    state[SLOTS] = empty_slots()


def _replace(state: SessionState, index: int, slot: Slot) -> None:
    current = slots(state)
    state[SLOTS] = (*current[:index], slot, *current[index + 1 :])


def _known_holdings_only(slot: Slot) -> Slot:
    percentages = slot.split.percentages
    if percentages.keys() <= HOLDINGS_BY_ID.keys():
        return slot
    known = {
        holding: percent for holding, percent in percentages.items() if holding in HOLDINGS_BY_ID
    }
    return replace(slot, split=replace(slot.split, percentages=known))
