"""The visitor's four splits, kept in their session.

Streamlit forgets a widget's value once the visitor leaves its page. So each split is kept under a
session key that no widget uses: the Design page copies the splits into its widgets before drawing
them, and every widget writes its change back. The functions take the session state as a plain
mapping, so they are tested without Streamlit.
"""

from collections.abc import MutableMapping
from typing import Any

from crashmodel.app.splits import EXAMPLE_SPLITS, Slot, Split, empty_slots, example_slots
from crashmodel.data.blocks import Block

type SessionState = MutableMapping[str | int, Any]

SLOTS = "slots"
"""The session key holding the four slots, which no widget uses."""
NAME = "name"
INCLUDED = "included"
TEMPLATE = "template"
TEMPLATES = {split.name: split for split in EXAMPLE_SPLITS}
"""The examples a slot can be filled from, by name."""


def ensure_started(state: SessionState) -> None:
    """Give a new session the examples, whichever page it opens first."""
    if SLOTS not in state:
        state[SLOTS] = example_slots()


def slots(state: SessionState) -> tuple[Slot, ...]:
    """Return the session's four slots."""
    stored: tuple[Slot, ...] = state[SLOTS]
    return stored


def widget_key(index: int, field: str) -> str:
    """Return the session key of one of a slot's widgets, such as ``slot0.name``."""
    return f"slot{index}.{field}"


def load_widgets(state: SessionState) -> None:
    """Copy each slot into its widgets' keys, so the widgets show it when drawn."""
    for index, slot in enumerate(slots(state)):
        state[widget_key(index, NAME)] = slot.split.name
        state[widget_key(index, INCLUDED)] = slot.included
        for block in Block:
            state[widget_key(index, block)] = slot.split.percentages.get(block, 0)


def commit(state: SessionState, index: int) -> None:
    """Store what a slot's widgets show as its split: the callback for each of its widgets."""
    percentages = {
        block: percent for block in Block if (percent := state[widget_key(index, block)])
    }
    split = Split(name=state[widget_key(index, NAME)], percentages=percentages)
    _replace(state, index, Slot(split=split, included=state[widget_key(index, INCLUDED)]))


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
