"""How the visitor's split names are shown on the page: never read as formatting."""

import re

_MARKDOWN_PUNCTUATION = re.compile(r"([\\`*_{}\[\]()#+\-.!|~<>$:&])")
"""Characters Markdown, or Streamlit's extensions to it, could read as formatting."""


def markdown_text(text: str) -> str:
    """Escape text a visitor typed, so Streamlit shows it exactly as typed."""
    return _MARKDOWN_PUNCTUATION.sub(r"\\\1", text)
