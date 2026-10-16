from decimal import Decimal
from pathlib import Path

import pytest

from tests.tools.helpers import GitRunner
from tests.tools.sentinels import (
    AMOUNT_LINE,
    DATE_LINE,
    NAME_LINE,
    SENTINEL_DENYLIST,
    TICKER_LINE,
    UNITS_LINE,
)
from tools import denylist
from tools.denylist import DenylistError, Entry, Matcher


@pytest.fixture
def entries(denylist: Path, tmp_path: Path) -> list[Entry]:
    return denylist_entries(denylist, tmp_path)


def denylist_entries(path: Path, tmp_path: Path) -> list[Entry]:
    return denylist.load_denylist(path, repository=tmp_path / "repo")


def matched_lines(text: str, entries: list[Entry]) -> set[int]:
    return {entry.line for entry in Matcher(entries).entries_in(text)}


def test_tokenise_splits_case_snake_case_digits_and_punctuation() -> None:
    assert denylist.tokenise("zebedeeQuartermaine_HTTPServer v2.0") == (
        "zebedee",
        "quartermaine",
        "http",
        "server",
        "v",
        "2",
        "0",
    )


def test_tokenise_ignores_accents_and_invisible_characters() -> None:
    assert denylist.tokenise("Zébe\u00addee Quarter\u200bmaine") == ("zebedee", "quartermaine")


@pytest.mark.parametrize(
    "text",
    [
        "Owner: Zebedee Quartermaine",
        "zebedee_quartermaine = True",
        "ZebedeeQuartermaine",
        "ZEBEDEE-QUARTERMAINE",
        "ZEBEDEEQUARTERMAINE",
        "zebedeequartermaine@example.com",
        "Quartermaine, Zebedee",
        "Zebedee J. Quartermaine",
        "Zébedee Quartermaine",
        "Zebe\u00addee Quartermaine",
    ],
)
def test_names_match_in_any_case_order_or_identifier_style(text: str, entries: list[Entry]) -> None:
    assert NAME_LINE in matched_lines(text, entries)


@pytest.mark.parametrize(
    "text",
    [
        "zqxwz is a different word",
        "Zebedee on his own",
        "Quartermaine",
        "Zebedee A B C Quartermaine",
    ],
)
def test_partial_names_and_longer_words_do_not_match(text: str, entries: list[Entry]) -> None:
    assert matched_lines(text, entries) == set()


def test_names_match_across_a_line_break_on_the_line_where_they_start(
    entries: list[Entry],
) -> None:
    matches = Matcher(entries).find("Intro\nThe owner is Zebedee\nQuartermaine.\n")
    assert [(line, entry.line) for line, entry in matches] == [(2, NAME_LINE)]


@pytest.mark.parametrize("text", ["McDonald", "MCDONALD", "owner=mcdonald", "Mc Donald"])
def test_camel_case_entries_match_however_the_text_is_cased(text: str) -> None:
    assert Matcher([denylist.parse_entry(1, "McDonald")]).entries_in(text)


def test_tickers_match_inside_identifiers(entries: list[Entry]) -> None:
    assert TICKER_LINE in matched_lines("n_zqxw = units_ZQXW.L", entries)


@pytest.mark.parametrize(
    "text",
    [
        "271,828",
        "271828.00",
        "£271,828",
        "VALUE = 271_828",
        "Value 271 828",
        "271\u202f828",
        "271,828.37",
        "about £271.8k",
        "about 272K",
        "27182800",
        "ZZZ,1,27182800",
        "row,7,2718.28",
    ],
)
def test_amounts_match_by_value_however_they_are_written(text: str, entries: list[Entry]) -> None:
    assert AMOUNT_LINE in matched_lines(text, entries)


@pytest.mark.parametrize("text", ["314.159", "314.16", "314.2", "31415.9", "17,314.16"])
def test_decimal_amounts_match_when_rounded_or_next_to_other_fields(
    text: str, entries: list[Entry]
) -> None:
    assert UNITS_LINE in matched_lines(text, entries)


@pytest.mark.parametrize("text", ["271827", "314", "2,718", "£0.27m", "10k"])
def test_different_or_indistinct_numbers_do_not_match(text: str, entries: list[Entry]) -> None:
    assert matched_lines(text, entries) == set()


@pytest.mark.parametrize("text", ["Total 12,346", "Total 12,345", "12,345.67", "£12.3k"])
def test_amounts_match_when_rounded_to_whole_units_or_abbreviated(text: str) -> None:
    assert Matcher([denylist.parse_entry(1, "12345.67")]).entries_in(text)


@pytest.mark.parametrize(("entry", "year"), [("1987.65", "1988"), ("200800", "2008")])
def test_rounded_or_rescaled_amounts_never_match_years(entry: str, year: str) -> None:
    assert Matcher([denylist.parse_entry(1, entry)]).entries_in(f"The crash of {year}") == []


@pytest.mark.parametrize(
    "text",
    [
        "2031-02-17",
        "2031-2-17",
        "2031-02-17T09:30:00Z",
        "date(2031, 2, 17)",
        "20310217",
        "17022031",
        "17/02/2031",
        "17.02.2031",
        "17/02/31",
        "02/17/2031",
        "17 February 2031",
        "17 Feb 2031",
        "17th February 2031",
        "Feb 17, 2031",
        "February 17th, 2031",
    ],
)
def test_iso_dates_match_common_spellings(text: str, entries: list[Entry]) -> None:
    assert DATE_LINE in matched_lines(text, entries)


@pytest.mark.parametrize("text", ["3 Sept 2031", "3rd Sep 2031", "September 3rd, 2031"])
def test_september_matches_every_abbreviation(text: str) -> None:
    assert Matcher([denylist.parse_entry(1, "2031-09-03")]).entries_in(text)


@pytest.mark.parametrize(
    ("day", "suffix"),
    [(1, "st"), (2, "nd"), (3, "rd"), (4, "th"), (11, "th"), (13, "th"), (22, "nd")],
)
def test_ordinal_suffixes(day: int, suffix: str) -> None:
    assert denylist.ordinal_suffix(day) == suffix


def test_amount_forms_include_pence_and_hundredths_when_distinctive() -> None:
    forms = denylist.amount_forms(Decimal("1234.5"))
    assert forms.exact == {Decimal("1234.5"), Decimal(123450), Decimal("12.345")}
    assert Decimal("1235") not in forms.rounded


def test_amount_forms_drop_figures_too_short_to_be_distinctive() -> None:
    forms = denylist.amount_forms(Decimal("68.5"))
    assert forms.exact == {Decimal("68.5")}
    assert forms.rounded == set()


def test_overlong_digit_runs_are_not_read_as_amounts() -> None:
    assert denylist.amounts_in("id 1234567890123456789012345") == set()
    assert denylist.abbreviated_amounts_in("id 1234567890123456789012345k") == set()


def test_load_denylist_skips_comments_and_blank_lines(entries: list[Entry]) -> None:
    assert [entry.line for entry in entries] == [
        NAME_LINE,
        TICKER_LINE,
        AMOUNT_LINE,
        UNITS_LINE,
        DATE_LINE,
    ]


def test_load_denylist_fails_closed_when_missing(tmp_path: Path) -> None:
    with pytest.raises(DenylistError, match="no denylist found"):
        denylist_entries(tmp_path / "absent.txt", tmp_path)


def test_load_denylist_fails_closed_when_empty(tmp_path: Path) -> None:
    path = tmp_path / "denylist.txt"
    path.write_text("# only a comment\n\n", encoding="utf-8")
    with pytest.raises(DenylistError, match="no entries"):
        denylist_entries(path, tmp_path)


def test_load_denylist_refuses_a_file_inside_the_repository(repo: Path) -> None:
    path = repo / "denylist.txt"
    path.write_text(SENTINEL_DENYLIST, encoding="utf-8")
    with pytest.raises(DenylistError, match="outside the repository"):
        denylist.load_denylist(path, repository=repo)


def test_load_denylist_ignores_a_byte_order_mark(tmp_path: Path) -> None:
    path = tmp_path / "denylist.txt"
    path.write_text("\ufeff271828\n", encoding="utf-8")

    assert Matcher(denylist_entries(path, tmp_path)).entries_in("271,828")


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("271828  # a comment\n", "line 1 has a comment after the entry"),
        ("# fine\n2031-02-30\n", "line 2 is not a real date"),
        ("£ $\n", "line 1 has no letters or digits"),
    ],
)
def test_load_denylist_names_the_malformed_line_without_repeating_it(
    tmp_path: Path, content: str, message: str
) -> None:
    path = tmp_path / "denylist.txt"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(DenylistError, match=message) as raised:
        denylist_entries(path, tmp_path)

    assert content.strip() not in str(raised.value)


def test_load_denylist_refuses_text_that_is_not_utf8(tmp_path: Path) -> None:
    path = tmp_path / "denylist.txt"
    path.write_bytes(b"Zo\xeb\n")

    with pytest.raises(DenylistError, match="not UTF-8"):
        denylist_entries(path, tmp_path)


def test_load_denylist_reports_a_file_it_cannot_read(tmp_path: Path) -> None:
    path = tmp_path / "denylist.txt"
    path.write_text("ZQXW\n", encoding="utf-8")
    path.chmod(0)

    try:
        with pytest.raises(DenylistError, match="cannot read the denylist"):
            denylist_entries(path, tmp_path)
    finally:
        path.chmod(0o600)


def test_load_denylist_refuses_the_repository_under_another_spelling(repo: Path) -> None:
    other_case = repo.parent / repo.name.upper() / "denylist.txt"
    if not other_case.parent.exists():
        pytest.skip("the file system is case-sensitive")
    (repo / "denylist.txt").write_text(SENTINEL_DENYLIST, encoding="utf-8")

    with pytest.raises(DenylistError, match="outside the repository"):
        denylist.load_denylist(other_case, repository=repo)


def test_denylist_path_comes_from_git_config_or_the_default(repo: Path, run_git: GitRunner) -> None:
    assert (
        denylist.configured_denylist_path(repo) == Path.home() / ".config/crashmodel/denylist.txt"
    )
    run_git("config", denylist.GIT_CONFIG_KEY, "/elsewhere/denylist.txt")
    assert denylist.configured_denylist_path(repo) == Path("/elsewhere/denylist.txt")


def test_an_entry_with_no_tokens_never_matches() -> None:
    assert Matcher([Entry(1, sequences=((),))]).find("anything at all") == []


@pytest.mark.parametrize(
    ("raw", "is_words"),
    [
        ("Zebedee Quartermaine", True),
        ("ZQXW", True),
        ("CW8G", True),
        ("271828", False),
        ("2031-02-17", False),
        ("2031-02", False),
        ("17/02/2031", False),
        ("12-34-56", False),
        ("QQ123456C", False),
        ("07700 900123", False),
    ],
)
def test_names_and_tickers_are_words_while_anything_else_with_digits_is_not(
    raw: str, is_words: bool
) -> None:
    assert denylist.parse_entry(1, raw).is_words is is_words
