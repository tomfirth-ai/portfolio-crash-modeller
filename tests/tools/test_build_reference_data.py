import io
import zipfile
from datetime import date
from pathlib import Path

import httpx
import pytest

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
GILT_CSV = "DATE,IUMMNPY\n31 Dec 2019,2\n31 Jan 2020,1.5\n28 Feb 2020,1.25\n31 Mar 2020,1\n"
BANK_RATE_CSV = "DATE,IUDBEDR\n02 Dec 2019,3.65\n02 Mar 2020,7.3\n01 Apr 2020,7.3\n"
RETRIEVED = date(2020, 4, 15)


def zipped(member: str, content: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member, content)
    return buffer.getvalue()


def publishers(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith(".zip"):
        return httpx.Response(200, content=zipped("H10_data.xml", H10_XML))
    code = request.url.params["SeriesCodes"]
    return httpx.Response(200, text={"IUMMNPY": GILT_CSV, "IUDBEDR": BANK_RATE_CSV}[code])


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
    assert build.parse_iadb(GILT_CSV, "IUMMNPY")[1] == (date(2020, 1, 31), 1.5)
    with pytest.raises(DownloadError, match="Bank of England CSV"):
        build.parse_iadb("<html>Error</html>", "IUMMNPY")


def test_months_that_have_not_ended_are_left_out() -> None:
    assert str(build.last_complete_month(RETRIEVED)) == "2020-03"


def test_every_series_and_its_source_note_are_written(tmp_path: Path) -> None:
    with client_for(httpx.MockTransport(publishers)) as client:
        written = build.build(client, RETRIEVED, tmp_path)

    assert len(written) == 6
    assert (tmp_path / "fed-h10/usd_per_gbp.csv").read_text() == (
        "month,usd_per_gbp\n2020-01,2.1000\n2020-02,2.2000\n2020-03,2.3000\n"
    )
    assert (tmp_path / "boe-gilt-yield/ten_year_par_yield.csv").read_text().splitlines()[1:3] == [
        "2019-12,2.0000",
        "2020-01,1.5000",
    ]
    cash = (tmp_path / "boe-bank-rate/cash_return.csv").read_text().splitlines()
    assert cash[1:] == ["2020-01,0.0031000000", "2020-02,0.0029000000", "2020-03,0.0061000000"]
    source = (tmp_path / "fed-h10/SOURCE.md").read_text()
    assert "Public domain" in source
    assert "Retrieved:** 2020-04-15" in source
    assert "SHA-256 `" in source


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
    assert capsys.readouterr().out.count("wrote ") == 6


def test_main_reports_a_failed_download(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def make_client() -> httpx.Client:
        def fail(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route")

        return client_for(httpx.MockTransport(fail))

    assert build.main(["--output", str(tmp_path)], make_client=make_client) == 1
    assert "build reference data: no route" in capsys.readouterr().err
