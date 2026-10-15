"""Synthetic text in the Kenneth R. French Data Library's two CSV layouts, for tests.

Every value is a round number made up here; no real data from the library is used or stored. The
layouts copy the real files' structure: CRLF line endings, the preamble, padding, the annual
section and the footer.
"""

import io
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

import httpx

from crashmodel.data.french import DEVELOPED_MARKETS, US_MARKET
from crashmodel.engine.months import Month

type Layout = Literal["us", "developed"]
type Row = tuple[float, float, float, float]
"""Mkt-RF, SMB, HML and RF, in percent."""

CRLF = "\r\n"
HEADER = ",Mkt-RF,SMB,HML,RF"
CYCLE: tuple[Row, ...] = (
    (1.00, 0.50, -0.50, 0.25),
    (-2.00, -1.00, 1.00, 0.25),
    (3.00, 0.00, 0.50, 0.25),
    (-1.00, 1.50, -1.00, 0.25),
)
US_WIDTH = 7
DEVELOPED_SLOT = 8
FIRST_MONTH = Month(2007, 1)


def _number(value: float) -> str:
    text = f"{value:.2f}"
    return "0.00" if text == "-0.00" else text


def _us_row(key: str, row: Sequence[float]) -> str:
    return ",".join([key.rjust(6), *(_number(value).rjust(US_WIDTH) for value in row)])


def _developed_row(key: str, row: Sequence[float]) -> str:
    fields = [key, *(_number(value) for value in row)]
    padded = [
        field + " " * (DEVELOPED_SLOT - len(fields[i + 1])) for i, field in enumerate(fields[:-1])
    ]
    return ",".join([*padded, fields[-1]])


def french_text(
    layout: Layout, *, start: Month = FIRST_MONTH, rows: Sequence[Row] | None = None
) -> str:
    """Return synthetic CSV text with monthly rows from ``start``, 24 by default."""
    monthly = list(rows) if rows is not None else [CYCLE[i % len(CYCLE)] for i in range(24)]
    months = [start + offset for offset in range(len(monthly))]
    keys = [f"{month.year:04d}{month.month:02d}" for month in months]
    vintage = keys[-1]
    annual = [(str(months[0].year + i), CYCLE[i % len(CYCLE)]) for i in range(2)]
    if layout == "us":
        render = _us_row
        lines = [
            f"This file was created using the {vintage} CRSP database.",
            "The 1-month TBill rate data are from a synthetic source. ",
            "The annual TBill return is compounded from the monthly rates. ",
            "",
            HEADER,
            *(render(key, row) for key, row in zip(keys, monthly, strict=True)),
            "",
            " Annual Factors: January-December ",
            HEADER,
            *(render(key, row) for key, row in annual),
            "",
            "Copyright 2026 Eugene F. Fama and Kenneth R. French",
        ]
    else:
        render = _developed_row
        lines = [
            f"This file was created using the {vintage} Bloomberg database.",
            "",
            "Missing data are indicated by -99.99.",
            "",
            "",
            "",
            HEADER,
            *(render(key, row) for key, row in zip(keys, monthly, strict=True)),
            "",
            "",
            "",
            " Annual Factors: January-December",
            HEADER,
            *(render(key, row) for key, row in annual),
        ]
    return CRLF.join(lines) + CRLF


def zipped(text: str, member: str = "F-F_Research_Data_Factors.csv") -> bytes:
    """Zip CSV text in memory, as the library serves it."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member, text)
    return buffer.getvalue()


LIBRARY_START = Month(2007, 1)
LIBRARY_END = Month(2024, 12)
"""The fake library's files cover both crash windows."""


@dataclass
class FakeLibrary:
    """A stand-in for the library's server, serving both files as synthetic text.

    Attributes:
        online: Whether it answers; when ``False``, every connection is refused.
        requests: The URL of every request it has received, in order.
    """

    online: bool = True
    requests: list[str] = field(default_factory=list)

    def client(self) -> httpx.Client:
        """Return an HTTP client whose requests go to this fake server."""
        return httpx.Client(transport=httpx.MockTransport(self._answer))

    def _answer(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)
        if not self.online:
            raise httpx.ConnectError("the fake library is offline")
        layouts: dict[str, Layout] = {US_MARKET.url: "us", DEVELOPED_MARKETS.url: "developed"}
        if url not in layouts:
            return httpx.Response(404)
        count = LIBRARY_END - LIBRARY_START + 1
        rows = [CYCLE[i % len(CYCLE)] for i in range(count)]
        text = french_text(layouts[url], start=LIBRARY_START, rows=rows)
        return httpx.Response(200, content=zipped(text))
