"""How split names are shown: never blank, never repeated, never read as formatting."""

import re
from collections.abc import Sequence

from crashmodel.app.splits import Slot

_MARKDOWN_PUNCTUATION = re.compile(r"([\\`*_{}\[\]()#+\-.!|~<>$:&])")
"""Characters Markdown, or Streamlit's extensions to it, could read as formatting."""


def display_names(slots: Sequence[Slot]) -> tuple[str, ...]:
    """Return a name for each slot's split, in order, that is never blank.

    A blank name becomes "Split 2" after its place. Among included splits a repeated name gets a
    number, such as "Balanced (2)", so that a chart or table never mixes two splits up.
    """
    shown: list[str] = []
    taken: set[str] = set()
    for number, slot in enumerate(slots, start=1):
        name = slot.split.name.strip() or f"Split {number}"
        if slot.included:
            base, copy = name, 1
            while name in taken:
                copy += 1
                name = f"{base} ({copy})"
            taken.add(name)
        shown.append(name)
    return tuple(shown)


def markdown_text(text: str) -> str:
    """Escape text a visitor typed, so Streamlit shows it exactly as typed."""
    return _MARKDOWN_PUNCTUATION.sub(r"\\\1", text)
