"""Text shared across pages."""

APP_NAME = "Portfolio crash modeller"

DISCLAIMER = (
    "Not investment advice. This is a learning and portfolio project: past performance, real or "
    "simulated, is not a reliable indicator of future results."
)

NOT_AFFILIATED = (
    "Index and fund names only identify what each model describes. This app is not affiliated "
    "with, sponsored or endorsed by any index provider or fund manager, and shows no index values "
    "or fund prices: every figure comes from a model built from published research and open data."
)
TRADE_MARKS = (
    "S&P 500 is a trade mark of Standard & Poor's Financial Services LLC. MSCI is a trade mark of "
    "MSCI Inc. FTSE is a trade mark of the London Stock Exchange Group companies. Fund names and "
    "tickers belong to their fund managers."
)

SOURCE_CODE = "Source code and design notes"
"""Label of the footer link to the repository, where the code, tests and decisions live."""

HOME_TITLE = "Home"
JOURNEY_SECTION = "Your journey"
"""The navigation section for the steps of the journey."""
REFERENCE_SECTION = "Reference"
"""The navigation section for pages that support the journey rather than form part of it."""


def page_title(page: str) -> str:
    """Return the browser tab title for a page, so each tab and bookmark says where it leads."""
    return f"{page} | {APP_NAME}"
