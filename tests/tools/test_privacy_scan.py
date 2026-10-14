from decimal import Decimal
from pathlib import Path

import pytest

from tests.tools.sentinels import SENTINEL_DENYLIST, GitRunner
from tools import privacy_scan as scan
from tools.privacy_scan import DenylistError

NAME_LINE, TICKER_LINE, AMOUNT_LINE, UNITS_LINE, DATE_LINE = 2, 3, 4, 5, 6


@pytest.fixture
def entries(denylist: Path, tmp_path: Path) -> list[scan.Entry]:
    return scan.load_denylist(denylist, repository=tmp_path / "repo")


def matched_lines(text: str, entries: list[scan.Entry]) -> set[int]:
    return {entry.line for entry in scan.matching_entries(text, entries)}


def test_tokenise_splits_case_snake_case_digits_and_punctuation() -> None:
    assert scan.tokenise("zebedeeQuartermaine_HTTPServer v2.0") == (
        "zebedee",
        "quartermaine",
        "http",
        "server",
        "v",
        "2",
        "0",
    )


@pytest.mark.parametrize(
    "text",
    [
        "Owner: Zebedee Quartermaine",
        "zebedee_quartermaine = True",
        "ZebedeeQuartermaine",
        "ZEBEDEE-QUARTERMAINE",
    ],
)
def test_names_match_in_any_case_or_identifier_style(text: str, entries: list[scan.Entry]) -> None:
    assert NAME_LINE in matched_lines(text, entries)


@pytest.mark.parametrize(
    "text", ["zqxwz is a different word", "Zebedee on his own", "Quartermaine"]
)
def test_partial_names_and_longer_words_do_not_match(text: str, entries: list[scan.Entry]) -> None:
    assert matched_lines(text, entries) == set()


def test_tickers_match_inside_identifiers(entries: list[scan.Entry]) -> None:
    assert TICKER_LINE in matched_lines("n_zqxw = units_ZQXW.L", entries)


@pytest.mark.parametrize("text", ["271,828", "271828.00", "£271,828", "27182800", "2718.28"])
def test_amounts_match_by_value_in_pounds_pence_or_hundredths(
    text: str, entries: list[scan.Entry]
) -> None:
    assert AMOUNT_LINE in matched_lines(text, entries)


@pytest.mark.parametrize("text", ["314.159", "314.16", "314.2", "31415.9"])
def test_decimal_amounts_match_when_rounded(text: str, entries: list[scan.Entry]) -> None:
    assert UNITS_LINE in matched_lines(text, entries)


@pytest.mark.parametrize("text", ["271827", "314", "2,718"])
def test_different_or_indistinct_numbers_do_not_match(text: str, entries: list[scan.Entry]) -> None:
    assert matched_lines(text, entries) == set()


@pytest.mark.parametrize(
    "text",
    ["2031-02-17", "20310217", "17/02/2031", "17 February 2031", "17 Feb 2031", "Feb 17, 2031"],
)
def test_iso_dates_match_common_spellings(text: str, entries: list[scan.Entry]) -> None:
    assert DATE_LINE in matched_lines(text, entries)


def test_amount_variants_drop_figures_too_short_to_be_distinctive() -> None:
    variants = scan.amount_variants(Decimal("68.5"))
    assert Decimal("68.5") in variants
    assert Decimal(6850) in variants
    assert Decimal("0.685") not in variants


def test_load_denylist_skips_comments_and_blank_lines(entries: list[scan.Entry]) -> None:
    assert [entry.line for entry in entries] == [2, 3, 4, 5, 6]


def test_load_denylist_fails_closed_when_missing(tmp_path: Path) -> None:
    with pytest.raises(DenylistError, match="no denylist found"):
        scan.load_denylist(tmp_path / "absent.txt", repository=tmp_path / "repo")


def test_load_denylist_fails_closed_when_empty(tmp_path: Path) -> None:
    path = tmp_path / "denylist.txt"
    path.write_text("# only a comment\n\n", encoding="utf-8")
    with pytest.raises(DenylistError, match="no entries"):
        scan.load_denylist(path, repository=tmp_path / "repo")


def test_load_denylist_refuses_a_file_inside_the_repository(repo: Path) -> None:
    path = repo / "denylist.txt"
    path.write_text(SENTINEL_DENYLIST, encoding="utf-8")
    with pytest.raises(DenylistError, match="outside the repository"):
        scan.load_denylist(path, repository=repo)


def test_staged_scan_reports_location_and_entry_without_echoing_the_match(
    repo: Path, run_git: GitRunner, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "notes.md").write_text("Fine line\nOwner: Zebedee Quartermaine\n", encoding="utf-8")
    run_git("add", "notes.md")

    exit_code = scan.main(["--staged", "--denylist", str(denylist)])

    output = capsys.readouterr().err
    assert exit_code == scan.EXIT_FINDINGS
    assert f"notes.md:2: matches denylist line {NAME_LINE}" in output
    assert "zebedee" not in output.lower()
    assert "quartermaine" not in output.lower()


def test_staged_scan_checks_file_names(
    repo: Path, run_git: GitRunner, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "zqxw_prices.csv").write_text("date,price\n", encoding="utf-8")
    run_git("add", "zqxw_prices.csv")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == scan.EXIT_FINDINGS
    assert f"file name matches denylist line {TICKER_LINE}" in capsys.readouterr().err


def test_staged_scan_blocks_binary_data_formats(
    repo: Path, run_git: GitRunner, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "portfolio.xlsx").write_bytes(b"PK\x03\x04\x00binary")
    run_git("add", "portfolio.xlsx")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == scan.EXIT_FINDINGS
    assert "binary data formats are never committed" in capsys.readouterr().err


def test_staged_scan_passes_clean_changes(repo: Path, run_git: GitRunner, denylist: Path) -> None:
    (repo / "README.md").write_text("A demo portfolio of 60% shares.\n", encoding="utf-8")
    run_git("add", "README.md")

    assert scan.main(["--staged", "--denylist", str(denylist)]) == scan.EXIT_CLEAN


def test_scan_fails_closed_without_a_denylist(repo: Path, tmp_path: Path) -> None:
    missing = tmp_path / "nowhere" / "denylist.txt"
    assert scan.main(["--staged", "--denylist", str(missing)]) == scan.EXIT_CONFIG_ERROR


def test_message_scan_checks_the_commit_message(repo: Path, tmp_path: Path, denylist: Path) -> None:
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("Add ZQXW prices\n", encoding="utf-8")

    assert scan.main(["--message", str(message), "--denylist", str(denylist)]) == scan.EXIT_FINDINGS


def test_history_scan_checks_commit_authors(repo: Path, run_git: GitRunner, denylist: Path) -> None:
    (repo / "a.txt").write_text("clean\n", encoding="utf-8")
    run_git("add", "a.txt")
    run_git("commit", "-q", "-m", "Clean message", env={"GIT_AUTHOR_NAME": "Zebedee Quartermaine"})

    assert scan.main(["--all-history", "--denylist", str(denylist)]) == scan.EXIT_FINDINGS


def test_push_scan_checks_commits_that_no_remote_has(
    repo: Path, run_git: GitRunner, denylist: Path
) -> None:
    (repo / "a.txt").write_text("unit count 314.159\n", encoding="utf-8")
    run_git("add", "a.txt")
    run_git("commit", "-q", "-m", "Add a file")

    assert scan.main(["--push", "--denylist", str(denylist)]) == scan.EXIT_FINDINGS
