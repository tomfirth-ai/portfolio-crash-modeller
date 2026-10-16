import io
import zipfile
from urllib.parse import urlsplit

import httpx
import pytest

from crashmodel.data import french
from crashmodel.data.french import (
    BIG,
    DEVELOPED_BY_SIZE,
    FIRMS_SECTION,
    PORTFOLIO_FILES,
    SIZE_SECTION,
    US_BY_SIZE,
    PortfolioFile,
    SourceUnavailableError,
    SourceUnreachableError,
    fetch_portfolios,
    parse_portfolios,
    read_zipped_csv,
)
from crashmodel.engine.months import Month
from tests.data.french_portfolio_text import (
    CRLF,
    FIRST_MONTH,
    US_HEADER,
    Cell,
    Values,
    portfolio_text,
    steady,
)
from tests.data.french_text import zipped

LAST_MONTH = FIRST_MONTH + 23
LOCAL_HEADER_BYTES = 30
"""The fixed part of a zip member's header; its name follows, then its compressed data."""


@pytest.mark.parametrize("file", PORTFOLIO_FILES, ids=lambda file: file.name)
def test_each_file_gives_its_portfolios_returns_firms_and_sizes(file: PortfolioFile) -> None:
    read = parse_portfolios(portfolio_text(file), file)
    assert set(read.portfolios) == set(file.portfolios)
    for portfolio in read.portfolios.values():
        assert (portfolio.returns.start, portfolio.returns.end) == (FIRST_MONTH, LAST_MONTH)
        assert portfolio.returns.values[:4] == pytest.approx((0.01, -0.02, 0.03, -0.01))
        assert set(portfolio.firms.values) == {10}
        assert set(portfolio.average_size.values) == {100}
    assert (read.vintage.month, read.vintage.database) == (LAST_MONTH, "Synthetic")


@pytest.mark.parametrize(
    "text",
    [
        french.BYTE_ORDER_MARK + portfolio_text(US_BY_SIZE),
        portfolio_text(US_BY_SIZE).replace(CRLF, "\n"),
        portfolio_text(US_BY_SIZE).replace(CRLF, "\r"),
    ],
    ids=["byte order mark", "LF", "CR"],
)
def test_byte_order_marks_and_any_line_ending_are_accepted(text: str) -> None:
    assert len(parse_portfolios(text, US_BY_SIZE).portfolios["Hi 10"].returns) == 24


def test_a_column_the_app_does_not_use_may_be_missing_throughout() -> None:
    """The real US file's first column, firms with no market value, is always missing."""
    assert "<= 0" in US_HEADER
    assert "<= 0" not in US_BY_SIZE.portfolios
    parse_portfolios(portfolio_text(US_BY_SIZE), US_BY_SIZE)


def missing_until(late: str, first: Month) -> Values:
    def values(column: str, month: Month) -> Cell:
        if column == late and month < first:
            return None, 0, None
        return steady(column, month)

    return values


def test_a_portfolio_that_starts_late_begins_at_its_first_complete_month() -> None:
    late = Month(2007, 4)
    text = portfolio_text(DEVELOPED_BY_SIZE, values=missing_until(BIG[0], late))
    read = parse_portfolios(text, DEVELOPED_BY_SIZE)
    assert read.portfolios[BIG[0]].returns.start == late
    assert read.portfolios[BIG[1]].returns.start == FIRST_MONTH


def gap_in(column: str, gap: Month) -> Values:
    def values(name: str, month: Month) -> Cell:
        return (None, 10, 100) if name == column and month == gap else steady(name, month)

    return values


def replaced(text: str, old: str, new: str) -> str:
    assert old in text
    return text.replace(old, new, 1)


def six(*, months: int = 24, values: Values = steady) -> str:
    return portfolio_text(DEVELOPED_BY_SIZE, months=months, values=values)


def every_month(cell: Cell) -> Values:
    def values(_column: str, _month: Month) -> Cell:
        return cell

    return values


def in_decimals(column: str, month: Month) -> Cell:
    """Returns of 1%, -2%, 3% and -1% written as decimals, as a file in the wrong unit would be."""
    percent, firms, size = steady(column, month)
    assert percent is not None
    return percent / 100, firms, size


def implausible(field: int, value: float) -> Values:
    def values(column: str, month: Month) -> Cell:
        cell = list(steady(column, month))
        if column == BIG[0] and month == FIRST_MONTH + 5:
            cell[field] = value
        return cell[0], cell[1], cell[2]

    return values


@pytest.mark.parametrize(
    ("text", "message"),
    [
        pytest.param(six()[six().index(CRLF) + 2 :], "vintage", id="no vintage line"),
        pytest.param("", "vintage", id="empty file"),
        pytest.param(
            replaced(six(), "  " + SIZE_SECTION, "  Average Size"), "missing", id="missing section"
        ),
        pytest.param(
            replaced(six(), "," + ",".join(("SMALL LoBM", "ME1 BM2")), ",SMALL,ME1 BM2"),
            "lacks",
            id="missing column",
        ),
        pytest.param(six().rstrip(CRLF).rsplit(CRLF, 2)[0], "different months", id="cut short"),
        pytest.param(
            replaced(six(), "200701,", "200701,1.00,"), "wrong number of fields", id="extra field"
        ),
        pytest.param(replaced(six(), "200701,", "2007-1,"), "YYYYMM", id="not a month"),
        pytest.param(six(months=11), "too few", id="too few months"),
        pytest.param(replaced(six(), "200703,", "200713,"), "from 1 to 12", id="month 13"),
        pytest.param(six().replace("200703,", "200704,"), "no gaps", id="skipped month"),
        pytest.param(six().replace("200704,", "200703,"), "does not follow", id="repeated month"),
        pytest.param(replaced(six(), "1.00", "nan"), "plain number", id="not a number"),
        pytest.param(
            six(values=gap_in(BIG[1], FIRST_MONTH + 6)), "missing data", id="gap after the start"
        ),
        pytest.param(
            six(values=every_month((None, 0, None))), "no complete month", id="nothing complete"
        ),
        pytest.param(six(values=implausible(0, -100.0)), "plausible range", id="lost everything"),
        pytest.param(six(values=implausible(0, 300.0)), "plausible range", id="garbled gain"),
        pytest.param(six(values=implausible(1, 10.5)), "whole number", id="part of a firm"),
        pytest.param(six(values=in_decimals), "decimals", id="decimals not percent"),
    ],
)
def test_anything_unexpected_is_refused(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_portfolios(text, DEVELOPED_BY_SIZE)


def test_sections_covering_different_months_are_refused() -> None:
    text = six()
    firms = text.index(FIRMS_SECTION)
    last_row = f"{CRLF}{LAST_MONTH.year:04d}{LAST_MONTH.month:02d},"
    cut = text.index(last_row, firms)
    shorter = text[:cut] + text[text.index(CRLF, cut + 2) :]
    with pytest.raises(ValueError, match="different months"):
        parse_portfolios(shorter, DEVELOPED_BY_SIZE)


def test_a_negative_firm_size_is_refused() -> None:
    with pytest.raises(ValueError, match="negative"):
        parse_portfolios(six(values=implausible(2, -5.0)), DEVELOPED_BY_SIZE)


def client_answering(response: httpx.Response) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda _request: response))


def test_a_file_is_fetched_and_read() -> None:
    content = zipped(portfolio_text(US_BY_SIZE), "Portfolios_Formed_on_ME.csv")
    with client_answering(httpx.Response(200, content=content)) as client:
        read = fetch_portfolios(client, US_BY_SIZE)
    assert set(read.portfolios) == set(US_BY_SIZE.portfolios)


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(404), "HTTP 404"),
        (httpx.Response(200, content=zipped("not a portfolio file")), "not as expected"),
    ],
)
def test_a_bad_answer_makes_the_source_unavailable(response: httpx.Response, message: str) -> None:
    with client_answering(response) as client, pytest.raises(SourceUnavailableError, match=message):
        fetch_portfolios(client, DEVELOPED_BY_SIZE)


@pytest.mark.parametrize(
    ("failure", "expected", "message"),
    [
        (httpx.ConnectError("refused"), SourceUnreachableError, "could not be reached"),
        (httpx.ReadTimeout("too slow"), SourceUnreachableError, "could not be reached"),
        (httpx.TooManyRedirects("a loop"), SourceUnavailableError, "download failed"),
    ],
    ids=["refused", "timed out", "redirect loop"],
)
def test_a_failed_download_makes_the_source_unavailable(
    failure: httpx.HTTPError, expected: type[SourceUnavailableError], message: str
) -> None:
    def fail(_request: httpx.Request) -> httpx.Response:
        raise failure

    with (
        httpx.Client(transport=httpx.MockTransport(fail)) as client,
        pytest.raises(expected, match=message) as raised,
    ):
        fetch_portfolios(client, DEVELOPED_BY_SIZE)
    assert type(raised.value) is expected


def test_every_file_comes_from_one_server() -> None:
    """So a server that cannot be reached for one file is not tried for the others."""
    assert len({urlsplit(file.url).hostname for file in PORTFOLIO_FILES}) == 1


def damaged_zip() -> bytes:
    """A compressed zip with a few bytes of its compressed data flipped, as a bad download has."""
    member = "Portfolios_Formed_on_ME.csv"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, portfolio_text(US_BY_SIZE))
    content = bytearray(buffer.getvalue())
    data = LOCAL_HEADER_BYTES + len(member)
    content[data + 10 : data + 16] = bytes(byte ^ 0xFF for byte in content[data + 10 : data + 16])
    return bytes(content)


def test_the_csv_is_read_from_the_zip_in_memory() -> None:
    assert read_zipped_csv(zipped("text")) == "text"


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"<html>Not found</html>", "not a readable zip"),
        (damaged_zip(), "not a readable zip"),
        (b"x" * (french.MAX_DOWNLOAD_BYTES + 1), "too large"),
        (zipped("text", member="notes.txt"), "exactly one CSV"),
        (zipped("caf\u00e9"), "not plain text"),
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
