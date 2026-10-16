"""The indexes and funds a split can hold, each linked to the model of the index it tracks.

Holding an index means holding the index itself, before any charges. A fund is a real tracker that
UK investors can buy; its facts are typed by hand into ``funds.csv`` from its key information
document, with that document's date (ADR 0005). Nothing here is a price or a return: every figure
the app shows for a fund or an index comes from its model.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from importlib.resources import files

from crashmodel.data.models import IndexModel
from crashmodel.engine.months import Month

PERCENT = Decimal(100)

type HoldingId = str
"""Lower-case letters, digits and underscores, so it can be part of a widget key."""
HOLDING_ID = re.compile(r"[a-z0-9_]+", re.ASCII)


@dataclass(frozen=True, kw_only=True)
class TrackedIndex:
    """An index that funds track, and the model that stands for it."""

    name: str
    model: IndexModel


S_AND_P_500 = TrackedIndex(name="S&P 500", model=IndexModel.US_LARGE)
MSCI_WORLD = TrackedIndex(name="MSCI World", model=IndexModel.DEVELOPED_LARGE)
FTSE_DEVELOPED = TrackedIndex(name="FTSE Developed", model=IndexModel.DEVELOPED_LARGE)
FTSE_ALL_WORLD = TrackedIndex(name="FTSE All-World", model=IndexModel.GLOBAL_LARGE)
MSCI_ACWI = TrackedIndex(name="MSCI ACWI", model=IndexModel.GLOBAL_LARGE)
FTSE_GLOBAL_ALL_CAP = TrackedIndex(name="FTSE Global All Cap", model=IndexModel.GLOBAL_ALL_CAP)
MSCI_ACWI_IMI = TrackedIndex(name="MSCI ACWI IMI", model=IndexModel.GLOBAL_ALL_CAP)
UK_GILT = TrackedIndex(name="10-year UK gilt", model=IndexModel.UK_GILTS)
BANK_RATE = TrackedIndex(name="Bank Rate", model=IndexModel.STERLING_CASH)
SONIA = TrackedIndex(name="SONIA", model=IndexModel.STERLING_CASH)
"""The overnight rate sterling money market funds aim to earn, which follows Bank Rate closely."""

TRACKED_INDEXES = (
    S_AND_P_500,
    MSCI_WORLD,
    FTSE_DEVELOPED,
    FTSE_ALL_WORLD,
    MSCI_ACWI,
    FTSE_GLOBAL_ALL_CAP,
    MSCI_ACWI_IMI,
    UK_GILT,
    BANK_RATE,
    SONIA,
)
"""Every index a holding is or tracks, in the order the picker groups them."""

INDEXES_BY_NAME: Mapping[str, TrackedIndex] = {index.name: index for index in TRACKED_INDEXES}


PROVIDERS = (
    "Amundi",
    "Fidelity",
    "HSBC",
    "Invesco",
    "iShares",
    "L&G",
    "SPDR",
    "UBS",
    "Vanguard",
    "Xtrackers",
)
"""The fund managers whose trackers are listed, so that the list follows a rule, not a choice."""


@dataclass(frozen=True, kw_only=True)
class Fund:
    """A real fund's facts, as its key information document gives them.

    Attributes:
        provider: The fund manager, one of :data:`PROVIDERS`.
        name: The share class's full name, as the fund manager writes it.
        ticker: Its London Stock Exchange ticker, for an exchange-traded fund; otherwise ``None``.
        yearly_charge: Its ongoing charge, in percent a year, as printed (``Decimal("0.07")``).
        launched: The month the share class was launched.
        documented: The date of the key information document the facts come from.
    """

    provider: str
    name: str
    ticker: str | None
    yearly_charge: Decimal
    launched: Month
    documented: date


@dataclass(frozen=True, kw_only=True)
class Holding:
    """Something a split can hold: an index itself, or a fund tracking it.

    Attributes:
        id: Its key in splits and widgets.
        index: The index it is, or tracks.
        fund: The fund, or ``None`` for the index itself, before any charges.
    """

    id: HoldingId
    index: TrackedIndex
    fund: Fund | None = None

    def __post_init__(self) -> None:
        """Check that the id can be part of a widget key.

        Raises:
            ValueError: If it cannot.
        """
        if not HOLDING_ID.fullmatch(self.id):
            raise ValueError(f"{self.id!r} is not lower-case letters, digits and underscores")

    @property
    def model(self) -> IndexModel:
        """The model that stands for the index."""
        return self.index.model

    @property
    def yearly_charge(self) -> float:
        """The yearly charge as a decimal fraction (0.0007 is 0.07%), or 0 for an index."""
        return 0.0 if self.fund is None else float(self.fund.yearly_charge / PERCENT)


INDEXES: tuple[Holding, ...] = (
    Holding(id="sp500", index=S_AND_P_500),
    Holding(id="msci_world", index=MSCI_WORLD),
    Holding(id="ftse_developed", index=FTSE_DEVELOPED),
    Holding(id="ftse_all_world", index=FTSE_ALL_WORLD),
    Holding(id="msci_acwi", index=MSCI_ACWI),
    Holding(id="ftse_global_all_cap", index=FTSE_GLOBAL_ALL_CAP),
    Holding(id="msci_acwi_imi", index=MSCI_ACWI_IMI),
    Holding(id="uk_gilt", index=UK_GILT),
    Holding(id="bank_rate", index=BANK_RATE),
)
"""Each index held directly, before any charges, in the order the picker lists them."""

FUND_FILE = "funds.csv"
"""The fund list beside this module: a header, then one line per fund, typed in by hand."""
FUND_COLUMNS = ("index", "provider", "name", "ticker", "yearly_charge", "launched", "documented")
"""Its columns. No field holds a comma, so the file needs no quoting."""
_CHARGE = re.compile(r"[0-9]+\.[0-9]+", re.ASCII)
_NOT_IN_ID = re.compile(r"[^a-z0-9]+")


def fund_id(fund: Fund) -> HoldingId:
    """Key a fund by its ticker in lower case or, without a ticker, by its name in snake case."""
    if fund.ticker is not None:
        return fund.ticker.lower()
    return _NOT_IN_ID.sub("_", fund.name.lower()).strip("_")


def parse_funds(text: str) -> tuple[Holding, ...]:
    """Read the fund list.

    Raises:
        ValueError: If the header is not the list's own, or a line has the wrong number of fields,
            names an index or provider not listed here, or has a malformed charge or date.
    """
    lines = text.splitlines()
    header = ",".join(FUND_COLUMNS)
    if not lines or lines[0] != header:
        raise ValueError(f"{FUND_FILE} must start with the header {header!r}")
    return tuple(_fund_line(number, line) for number, line in enumerate(lines[1:], start=2))


def _fund_line(number: int, line: str) -> Holding:
    where = f"{FUND_FILE}:{number}"
    fields = line.split(",")
    if len(fields) != len(FUND_COLUMNS):
        raise ValueError(f"{where}: expected {len(FUND_COLUMNS)} fields")
    index, provider, name, ticker, charge, launched, documented = fields
    if index not in INDEXES_BY_NAME:
        raise ValueError(f"{where}: {index!r} is not an index listed here")
    if provider not in PROVIDERS:
        raise ValueError(f"{where}: {provider!r} is not a listed provider")
    if not _CHARGE.fullmatch(charge):
        raise ValueError(f"{where}: expected a charge in percent, such as 0.12, not {charge!r}")
    try:
        fund = Fund(
            provider=provider,
            name=name,
            ticker=ticker or None,
            yearly_charge=Decimal(charge),
            launched=Month.parse(launched),
            documented=date.fromisoformat(documented),
        )
        return Holding(id=fund_id(fund), index=INDEXES_BY_NAME[index], fund=fund)
    except ValueError as error:
        raise ValueError(f"{where}: {error}") from None


FUNDS = parse_funds(files(__package__).joinpath(FUND_FILE).read_text(encoding="utf-8"))
"""Every listed fund, in the list's order; the picker sorts them itself."""


def _in_picker_order(holdings: tuple[Holding, ...]) -> tuple[Holding, ...]:
    """Group holdings by index; within each, the index itself comes first, then funds by name."""

    def place(holding: Holding) -> tuple[int, int, str]:
        name = "" if holding.fund is None else holding.fund.name.casefold()
        return TRACKED_INDEXES.index(holding.index), holding.fund is not None, name

    return tuple(sorted(holdings, key=place))


CATALOGUE: tuple[Holding, ...] = _in_picker_order(INDEXES + FUNDS)
"""Everything a split can hold, in the order the picker lists it."""

HOLDINGS_BY_ID: Mapping[HoldingId, Holding] = {holding.id: holding for holding in CATALOGUE}
