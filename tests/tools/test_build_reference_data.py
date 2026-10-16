import io
import zipfile
from datetime import date
from pathlib import Path

import httpx
import pytest

from crashmodel.data.reference_data import FIVE_YEAR_ZERO_YIELD, USD_PER_GBP
from crashmodel.engine.months import Month, MonthlySeries
from tools import build_reference_data as build
from tools.build_reference_data import DownloadError

H10_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<message:MessageGroup xmlns:message="urn:message" xmlns:frb="urn:frb" xmlns:kf="urn:kf">
  <frb:DataSet>
    <kf:Series SERIES_NAME="RXI_N.M.UK">
      <frb:Obs OBS_STATUS="A" OBS_VALUE="9.0000" TIME_PERIOD="2020-01" />
    </kf:Series>
    <kf:Series SERIES_NAME="RXI$US_N.B.UK">
      <frb:Annotations><frb:Note>United Kingdom Pound (USD per GBP)</frb:Note></frb:Annotations>
      <frb:Obs OBS_STATUS="A" OBS_VALUE="2.0000" TIME_PERIOD="2020-01-30" />
      <frb:Obs OBS_STATUS="A" OBS_VALUE="2.1000" TIME_PERIOD="2020-01-31" />
      <frb:Obs OBS_STATUS="ND" OBS_VALUE="-9999" TIME_PERIOD="2020-02-03" />
      <frb:Obs OBS_STATUS="A" OBS_VALUE="2.2000" TIME_PERIOD="2020-02-28" />
      <frb:Obs OBS_STATUS="A" OBS_VALUE="2.3000" TIME_PERIOD="2020-03-31" />
      <frb:Obs OBS_STATUS="A" OBS_VALUE="2.4000" TIME_PERIOD="2020-04-01" />
    </kf:Series>
  </frb:DataSet>
</message:MessageGroup>
"""
BANK_RATE_CSV = (
    "DATE,IUDBEDR\n02 Dec 2019,3.65\n02 Jan 2020,3.65\n03 Feb 2020,3.65\n02 Mar 2020,7.3\n"
    "01 Apr 2020,7.3\n"
)
SONIA_CSV = "DATE,IUDSOIA\n02 Jan 2020,7.3\n03 Feb 2020,7.3\n02 Mar 2020,7.3\n01 Apr 2020,7.3\n"
"""SONIA here begins on 2 January 2020, at twice Bank Rate, so the join shows."""
RETRIEVED = date(2020, 4, 15)


def yield_csv(code: str) -> str:
    return f"DATE,{code}\n31 Dec 2019,0.5\n31 Jan 2020,-0.25\n28 Feb 2020,0.75\n31 Mar 2020,1\n"


IADB_CSVS = {
    "IUDBEDR": BANK_RATE_CSV,
    "IUDSOIA": SONIA_CSV,
    **{code: yield_csv(code) for code in ("IUMSNZC", "IUMMNZC", "IUMLNZC", "IUMSNPY")},
}


def zipped(member: str, content: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member, content)
    return buffer.getvalue()


def publishers(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith(".zip"):
        return httpx.Response(200, content=zipped("H10_data.xml", H10_XML))
    return httpx.Response(200, text=IADB_CSVS[request.url.params["SeriesCodes"]])


def client_for(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler)


def test_the_pound_series_is_read_and_days_without_data_skipped() -> None:
    days = build.parse_h10(H10_XML, "RXI$US_N.B.UK")
    assert days[0] == (date(2020, 1, 30), 2.0)
    assert len(days) == 5


def test_a_missing_series_is_refused() -> None:
    with pytest.raises(DownloadError, match="found 0"):
        build.parse_h10(H10_XML, "RXI$XX_N.B.XX")


def test_a_series_that_appears_twice_is_refused() -> None:
    second = b'<kf:Series SERIES_NAME="RXI$US_N.B.UK" /></frb:DataSet>'
    with pytest.raises(DownloadError, match="found 2"):
        build.parse_h10(H10_XML.replace(b"</frb:DataSet>", second), "RXI$US_N.B.UK")


def test_bank_of_england_csv_is_read_and_error_pages_refused() -> None:
    assert build.parse_iadb(yield_csv("IUMSNZC"), "IUMSNZC")[1] == (date(2020, 1, 31), -0.25)
    with pytest.raises(DownloadError, match="Bank of England CSV"):
        build.parse_iadb("<html>Error</html>", "IUMSNZC")


def test_a_blank_value_or_a_missing_month_names_the_series() -> None:
    with pytest.raises(DownloadError, match="IUMSNZC: the row '31 Jan 2020,'"):
        build.parse_iadb("DATE,IUMSNZC\n31 Jan 2020,\n", "IUMSNZC")
    january_and_march = [(date(2020, 1, 31), 1.0), (date(2020, 3, 31), 1.0)]
    with pytest.raises(DownloadError, match="IUMSNZC"):
        build._month_ends(january_and_march, "IUMSNZC")


def test_months_that_have_not_ended_are_left_out() -> None:
    assert str(build.last_complete_month(RETRIEVED)) == "2020-03"


def test_every_series_and_its_source_note_are_written(tmp_path: Path) -> None:
    with client_for(httpx.MockTransport(publishers)) as client:
        written = build.build(client, RETRIEVED, tmp_path)

    assert len(written) == 10
    assert (tmp_path / "fed-h10/usd_per_gbp.csv").read_text() == (
        "month,usd_per_gbp\n2020-01,2.1000\n2020-02,2.2000\n2020-03,2.3000\n"
    )
    source = (tmp_path / "fed-h10/SOURCE.md").read_text()
    assert "Public domain" in source
    assert "Retrieved:** 2020-04-15" in source
    assert "SHA-256 `" in source


def test_the_yield_curve_series_share_one_folder_and_note(tmp_path: Path) -> None:
    with client_for(httpx.MockTransport(publishers)) as client:
        build.build(client, RETRIEVED, tmp_path)

    folder = tmp_path / "boe-yield-curve"
    names = ("five_year_zero_yield", "ten_year_zero_yield", "twenty_year_zero_yield")
    for name in (*names, "five_year_par_yield"):
        rows = (folder / f"{name}.csv").read_text().splitlines()
        assert rows[:3] == [f"month,{name}", "2019-12,0.5000", "2020-01,-0.2500"]
    note = (folder / "SOURCE.md").read_text()
    assert note.startswith("# Yields from British Government Securities")
    assert all(f"`{name}.csv`" in note for name in names)
    assert all(code in note for code in ("IUMSNZC", "IUMMNZC", "IUMLNZC", "IUMSNPY"))


def test_cash_earns_bank_rate_until_sonia_begins_and_sonia_after(tmp_path: Path) -> None:
    """Bank Rate of 3.65% (0.0001 a day) carries over 1 January; SONIA of 7.3% follows."""
    with client_for(httpx.MockTransport(publishers)) as client:
        build.build(client, RETRIEVED, tmp_path)

    folder = tmp_path / "boe-sterling-cash"
    cash = (folder / "cash_return.csv").read_text().splitlines()
    assert cash[1:] == ["2020-01,0.0061180343", "2020-02,0.0058162693", "2020-03,0.0062186360"]
    bank_rate = (folder / "bank_rate.csv").read_text().splitlines()
    assert bank_rate[1:] == ["2019-12,3.6500", "2020-01,3.6500", "2020-02,3.6500", "2020-03,7.3000"]
    note = (folder / "SOURCE.md").read_text()
    assert '"SONIA" are registered trade marks of the Bank of England' in note
    assert "2 January 2020" in note
    assert "not by the Bank" in note


def test_a_later_rate_takes_over_from_the_day_it_begins() -> None:
    earlier = [(date(2020, 1, 1), 1.0), (date(2020, 1, 3), 2.0)]
    later = [(date(2020, 1, 3), 3.0), (date(2020, 1, 4), 4.0)]
    assert build.spliced(earlier, later) == [(date(2020, 1, 1), 1.0), *later]


def test_a_folder_holds_series_from_one_dataset_only() -> None:
    values = MonthlySeries(Month(2020, 1), (1.0,))
    outputs: list[build.Output] = [
        (USD_PER_GBP, values, [], "x"),
        (FIVE_YEAR_ZERO_YIELD, values, [], "y"),
    ]
    with pytest.raises(ValueError, match="same dataset"):
        build.render_source(outputs, RETRIEVED)


def test_a_failed_download_stops_the_build(tmp_path: Path) -> None:
    def refuse(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": "ErrorPage.asp"})

    with (
        client_for(httpx.MockTransport(refuse)) as client,
        pytest.raises(DownloadError, match="302"),
    ):
        build.build(client, RETRIEVED, tmp_path)


def test_main_builds_into_the_given_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def make_client() -> httpx.Client:
        return client_for(httpx.MockTransport(publishers))

    argv = ["--retrieved", "2020-04-15", "--output", str(tmp_path)]
    assert build.main(argv, make_client=make_client) == 0
    assert capsys.readouterr().out.count("wrote ") == 10


def test_main_reports_a_failed_download(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def make_client() -> httpx.Client:
        def fail(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route")

        return client_for(httpx.MockTransport(fail))

    assert build.main(["--output", str(tmp_path)], make_client=make_client) == 1
    assert "build reference data: no route" in capsys.readouterr().err


def build_with_h10(xml: bytes, output: Path) -> list[Path]:
    """Build from the usual publishers, but with this H.10 file."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".zip"):
            return httpx.Response(200, content=zipped("H10_data.xml", xml))
        return publishers(request)

    with client_for(httpx.MockTransport(handler)) as client:
        return build.build(client, RETRIEVED, output)


def test_a_daily_month_is_kept_only_once_a_later_day_is_published(tmp_path: Path) -> None:
    """Here the newest rate is from 27 March, so March's month-end rate is not known yet."""
    april = b'      <frb:Obs OBS_STATUS="A" OBS_VALUE="2.4000" TIME_PERIOD="2020-04-01" />\n'
    lagging = H10_XML.replace(april, b"").replace(b"2020-03-31", b"2020-03-27")
    build_with_h10(lagging, tmp_path)

    rates = (tmp_path / "fed-h10/usd_per_gbp.csv").read_text().splitlines()
    assert rates[-1] == "2020-02,2.2000"


def test_a_value_out_of_range_is_caught_before_it_is_written(tmp_path: Path) -> None:
    implausible = H10_XML.replace(b'OBS_VALUE="2.2000"', b'OBS_VALUE="99.0000"')
    with pytest.raises(ValueError, match="outside"):
        build_with_h10(implausible, tmp_path)
    assert not (tmp_path / "fed-h10/usd_per_gbp.csv").exists()
