import httpx
import pytest

from crashmodel.data import french
from crashmodel.data.french import (
    DEVELOPED_MARKETS,
    US_MARKET,
    SourceUnavailableError,
    parse_market_returns,
    read_zipped_csv,
)
from crashmodel.engine.months import Month
from tests.data.french_text import CYCLE, Layout, Row, french_text, zipped

START = Month(2007, 1)


@pytest.mark.parametrize("layout", ["us", "developed"])
def test_both_layouts_give_monthly_total_returns_and_the_vintage(layout: Layout) -> None:
    result = parse_market_returns(french_text(layout, start=START))
    assert (result.returns.start, len(result.returns)) == (START, 24)
    assert result.returns[START] == pytest.approx((1.00 + 0.25) / 100)
    assert result.returns[START + 1] == pytest.approx((-2.00 + 0.25) / 100)
    assert result.vintage.month == START + 23
    assert result.vintage.database == ("CRSP" if layout == "us" else "Bloomberg")


def test_the_annual_section_is_never_read_as_months() -> None:
    assert parse_market_returns(french_text("us")).returns.end == START + 23


@pytest.mark.parametrize(
    "text",
    [
        "﻿" + french_text("us"),
        french_text("us").replace("\r\n", "\n"),
        french_text("developed").replace("\r\n", "\r"),
    ],
)
def test_byte_order_marks_and_any_line_ending_are_accepted(text: str) -> None:
    assert len(parse_market_returns(text).returns) == 24


def replace_row(layout: Layout, index: int, row: Row) -> str:
    rows = [CYCLE[i % len(CYCLE)] for i in range(24)]
    rows[index] = row
    return french_text(layout, rows=rows)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "vintage"),
        (french_text("us").replace("using the", "from the"), "vintage"),
        (french_text("us").replace(",Mkt-RF,SMB,HML,RF", ",Mkt-RF,SMB,HML,RMW,RF"), "header"),
        (replace_row("us", 3, (-99.99, 0.0, 0.0, 0.25)), "missing data"),
        (replace_row("developed", 3, (1.0, 0.0, 0.0, -999.0)), "missing data"),
        (replace_row("us", 3, (75.0, 0.0, 0.0, 0.25)), "market return"),
        (replace_row("us", 3, (1.0, 0.0, 0.0, 4.0)), "risk-free"),
        (french_text("us").replace("200703,", "200713,"), "month must be from 1 to 12"),
        (french_text("us").replace("200703,", "200704,", 1), "no gaps"),
        (french_text("us").replace("   1.00,   0.50", "    nan,   0.50", 1), "plain number"),
        (french_text("us").replace("   0.25\r\n", "   0.25,   9.99\r\n", 1), "number of fields"),
        (french_text("us").replace("200703,", "  2007,"), "YYYYMM"),
        ("\r\n".join(french_text("us").split("\r\n")[:12]), "does not end"),
        (french_text("us", rows=CYCLE * 2), "too few"),
        (french_text("us", rows=[(0.10, 0.0, 0.0, 0.05)] * 12), "decimals, not percent"),
    ],
)
def test_anything_unexpected_is_refused(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_market_returns(text)


def test_the_csv_is_read_from_the_zip_in_memory() -> None:
    assert read_zipped_csv(zipped("text")) == "text"


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"<html>Not found</html>", "not a zip"),
        (b"x" * (french.MAX_DOWNLOAD_BYTES + 1), "too large"),
        (zipped("text", member="notes.txt"), "exactly one CSV"),
        (zipped("café"), "not plain text"),
    ],
)
def test_a_download_that_is_not_one_ascii_csv_in_a_zip_is_refused(
    content: bytes, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        read_zipped_csv(content)


def test_an_oversized_csv_inside_the_zip_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(french, "MAX_CSV_BYTES", 100)
    with pytest.raises(ValueError, match="CSV file is too large"):
        read_zipped_csv(zipped("x" * 200))


def client_answering(response: httpx.Response) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda _request: response))


def test_a_file_is_fetched_and_read() -> None:
    response = httpx.Response(200, content=zipped(french_text("developed")))
    with client_answering(response) as client:
        result = french.fetch_market_returns(client, DEVELOPED_MARKETS)
    assert len(result.returns) == 24


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(404), "HTTP 404"),
        (httpx.Response(200, content=b"<html>maintenance</html>"), "not as expected"),
    ],
)
def test_a_bad_answer_makes_the_source_unavailable(response: httpx.Response, message: str) -> None:
    with client_answering(response) as client, pytest.raises(SourceUnavailableError, match=message):
        french.fetch_market_returns(client, US_MARKET)


def test_a_failed_connection_makes_the_source_unavailable() -> None:
    def refuse(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow")

    with (
        httpx.Client(transport=httpx.MockTransport(refuse)) as client,
        pytest.raises(SourceUnavailableError, match="download failed"),
    ):
        french.fetch_market_returns(client, US_MARKET)
