"""Text shared across pages."""

APP_NAME = "Portfolio crash modeller"

DISCLAIMER = (
    "Not investment advice. This is a learning and portfolio project: past performance, real or "
    "simulated, is not a reliable indicator of future results."
)

ADVICE_WORDS = frozenset({"best", "recommended", "safe", "should", "suitable"})
"""Words that would present a split as advice. User-facing copy never uses them."""


def page_title(page: str) -> str:
    """Return the browser tab title for a page, so each tab and bookmark says where it leads."""
    return f"{page} | {APP_NAME}"
