"""What the How it works page says: the method in plain words, what it leaves out, and the project.

The decision records on GitHub give the full reasons; this page is for a visitor who wants to know
where the figures come from without reading them.
"""

from dataclasses import dataclass

TITLE = "How it works"
INTRODUCTION = (
    "Every figure in this app comes from a model of an index, built from published research and "
    "open data. This page says how, in plain words, and what the models leave out."
)


@dataclass(frozen=True, kw_only=True)
class Section:
    """One part of the page: a heading and its paragraphs, in Markdown."""

    heading: str
    paragraphs: tuple[str, ...]


WHAT_IT_SHOWS = Section(
    heading="What the app shows",
    paragraphs=(
        "You choose up to four splits of funds and indexes, and the app shows how £100 in each "
        "would have done through four real crashes: the 2000-03 dot-com crash, the 2007-09 "
        "financial crisis, the 2020 Covid crash and the 2022-23 bond crash.",
        "Each crash has a crash phase, when markets fell, inside a longer window that shows "
        "whether each split got back to where it started. For each split you see its worst fall "
        "in the crash phase, how many months it took to reach its low and to get back, and what "
        "£100 became by the end of the window, in pounds before inflation.",
        "A split is managed in one of two ways. Kept at its percentages: put back to them at the "
        "end of every month. Left alone: bought once and never changed.",
    ),
)
SHARES = Section(
    heading="Shares",
    paragraphs=(
        "Share indexes are rebuilt from the Kenneth R. French Data Library's portfolios of "
        "companies grouped by size, in the US, in developed countries and in emerging countries, "
        "each weighted by its companies' market value. The S&P 500 is modelled as the largest US "
        "companies; MSCI World and FTSE Developed as the large and mid-sized companies of "
        "developed countries; FTSE All-World and MSCI ACWI as those of developed and emerging "
        "countries together; and FTSE Global All Cap and MSCI ACWI IMI as companies of every size, "
        "worldwide.",
        "Their returns, in dollars, are turned into pounds at month-end exchange rates published "
        "by the Federal Reserve. The share data is fetched when the app runs and is never written "
        "to disk.",
    ),
)
GILTS_AND_CASH = Section(
    heading="Gilts and cash",
    paragraphs=(
        "UK government bonds, gilts, are worked out from the Bank of England's estimated gilt "
        "yield curve. Gilt indexes of all maturities and of over 15 years are modelled as a ladder "
        "of gilts that each keep the coupon they were issued with, revalued every month as yields "
        "move. Short-dated gilts are modelled as half a 5-year gilt and half cash.",
        "Cash earns SONIA, the average rate banks pay to borrow sterling overnight, compounded "
        "daily, with the Bank of England's Bank Rate before SONIA began in 1997.",
    ),
)
FUNDS = Section(
    heading="Funds",
    paragraphs=(
        "A fund is modelled as the index it tracks, less its ongoing charge. Each fund's name, "
        "ticker, charge and launch month are typed in from its key information document, whose "
        "date its help text gives. No fund prices or index values are used.",
        "A fund launched after a crash began is still shown, modelled like every other, with a "
        "note saying when it was launched.",
    ),
)
LIMITS = Section(
    heading="What the models leave out",
    paragraphs=(
        "These are simulated figures, and real funds and indexes did differently: the models "
        "group companies by size and hold gilts in fixed shares by the time they have left to "
        "run, rather than following each index's own rules.",
        "The models use month-end values, so a fall within a month could have been deeper. Tax, "
        "dealing costs and platform charges are not taken off. Getting back to an earlier high in "
        "pounds is not the same as getting back your spending power.",
        "Past performance, real or simulated, is not a reliable indicator of future results, and "
        "nothing in this app is investment advice.",
    ),
)
PRIVACY = Section(
    heading="Privacy",
    paragraphs=(
        "The app asks for nothing personal and keeps nothing you type: your splits stay only while "
        "your tab is open. It is hosted on Streamlit Community Cloud, which records anonymous "
        "usage under its own [privacy policy](https://streamlit.io/privacy-policy). The app itself "
        "sets only Streamlit's security cookie, and your browser remembers the sidebar and colour "
        "theme you chose for this site.",
    ),
)

DECISION_RECORDS = (
    ("how the stress test works", "0003-stress-test-method.md"),
    ("how funds are modelled", "0005-real-funds-modelled.md"),
    ("how gilts and cash are modelled", "0006-gilts-and-sonia.md"),
    ("which data the app may store", "0002-hosted-data-mode.md"),
)
"""The decision records a visitor is most likely to want, as (what it explains, file name)."""


def sections(repository: str | None) -> tuple[Section, ...]:
    """Return the page's sections, linking the decision records and the code when they exist."""
    return (
        WHAT_IT_SHOWS,
        SHARES,
        GILTS_AND_CASH,
        FUNDS,
        LIMITS,
        _reasons(repository),
        _about(repository),
        PRIVACY,
    )


def _reasons(repository: str | None) -> Section:
    if repository is None:
        records = "decision records stored with the code"
    else:
        links = [
            f"[{subject}]({repository}/blob/main/docs/decisions/{name})"
            for subject, name in DECISION_RECORDS
        ]
        records = f"decision records: {', '.join(links[:-1])} and {links[-1]}"
    return Section(
        heading="Why it works this way",
        paragraphs=(f"Each choice above, and why it was made, is set out in the {records}.",),
    )


def _about(repository: str | None) -> Section:
    code = "the code" if repository is None else f"[the code]({repository})"
    return Section(
        heading="About this project",
        paragraphs=(
            f"A learning and portfolio project, built in the open: {code}, its tests and every "
            "design decision are public. Choosing one split and tracking it month by month come "
            "next.",
        ),
    )
