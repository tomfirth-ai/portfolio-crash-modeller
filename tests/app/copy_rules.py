"""The rules every sentence a visitor can read must follow, from CLAUDE.md.

No dash lookalikes, British spelling, and nothing that presents a split as advice.
"""

import re

from tools.check_style import DASH_LOOKALIKES, find_american_spellings

ADVICE = re.compile(
    r"\b(?:best|ought|recommend\w*|safe(?:r|st|ly|ty)?|should\w*|suitab\w*)\b", re.IGNORECASE
)
"""Words that would present a split as advice, in any of their forms."""

STREAMLIT_DIRECTIVES = re.compile(r":material/\w+:|:[a-z]+(?:-badge|-background)?(?=\[)")
"""Streamlit's own Markdown for icons and colours, such as ``:gray-badge[``, which no one reads."""


def copy_problems(text: str) -> list[str]:
    """Return every way the visible text breaks the copy rules, or an empty list."""
    text = STREAMLIT_DIRECTIVES.sub("", text)
    problems = [
        f"dash lookalike U+{ord(character):04X}" for character in set(text) & DASH_LOOKALIKES
    ]
    problems += [problem.message for problem in find_american_spellings(text, "copy")]
    problems += [f"reads as advice: '{match[0]}'" for match in ADVICE.finditer(text)]
    return problems
