import shutil
from pathlib import Path

import pytest

from tests.tools.helpers import GitRunner, png, png_chunk
from tools import check_hygiene
from tools._report import EXIT_CLEAN, EXIT_PROBLEMS
from tools.policy import BLOCKED_FORMAT, BLOCKED_SUFFIXES, FUND_CATALOGUE

PUBLIC_EXAMPLE_ISIN = "US0378331005"
"""A well-known, public ISIN with a valid check digit, used only as test data."""

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRIVATE = "private or local file is tracked"


def test_isin_check_digit_is_validated() -> None:
    assert check_hygiene.is_valid_isin(PUBLIC_EXAMPLE_ISIN)
    assert not check_hygiene.is_valid_isin("US0378331006")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("private/notes.md", PRIVATE),
        ("docs/private/notes.md", PRIVATE),
        ("local/crashmodel.db", PRIVATE),
        ("CLAUDE.local.md", PRIVATE),
        (".claude/settings.local.json", PRIVATE),
        (".streamlit/secrets.toml", PRIVATE),
        ("config/denylist.txt", PRIVATE),
        ("data/prices.xlsx", BLOCKED_FORMAT),
        ("statement.PDF", BLOCKED_FORMAT),
        ("store.db-wal", BLOCKED_FORMAT),
        ("store.sqlite-journal", BLOCKED_FORMAT),
        ("screenshot.png", "images belong in docs/img/ after review"),
        (f"data/{PUBLIC_EXAMPLE_ISIN}.csv", "file name contains an ISIN"),
        (
            f"src/crashmodel/data/reference/x/{PUBLIC_EXAMPLE_ISIN}.csv",
            "file name contains an ISIN",
        ),
    ],
)
def test_private_blocked_misplaced_and_identifying_paths_are_flagged(
    path: str, expected: str
) -> None:
    assert any(expected in problem for problem in check_hygiene.path_problems(path))


@pytest.mark.parametrize(
    "path",
    [
        "docs/img/home.png",
        "src/crashmodel/__init__.py",
        "tools/denylist.py",
        "README.md",
        f"tests/{PUBLIC_EXAMPLE_ISIN}.csv",
    ],
)
def test_allowed_paths_pass(path: str) -> None:
    assert list(check_hygiene.path_problems(path)) == []


@pytest.mark.parametrize(
    "line",
    [
        f"instrument: {PUBLIC_EXAMPLE_ISIN}",
        f"id: isin_{PUBLIC_EXAMPLE_ISIN}",
        f"{PUBLIC_EXAMPLE_ISIN}_prices: x",
    ],
)
def test_valid_isins_in_config_are_flagged(line: str) -> None:
    problems = list(check_hygiene.content_problems("config/demo.yaml", f"{line}\n".encode()))
    assert problems == [f"contains an ISIN; {check_hygiene.ISIN_RULE}"]


@pytest.mark.parametrize(
    "line", ["id: US0378331006", f"id: {PUBLIC_EXAMPLE_ISIN.lower()}", "name: portfolio005"]
)
def test_bad_check_digits_and_lower_case_names_pass(line: str) -> None:
    assert list(check_hygiene.content_problems("config/demo.yaml", f"{line}\n".encode())) == []


def test_an_isin_in_the_fund_list_is_flagged() -> None:
    line = f"S&P 500,Vanguard,Example {PUBLIC_EXAMPLE_ISIN} UCITS ETF,,0.07,2019-05,2026-01-01\n"
    problems = list(check_hygiene.content_problems(FUND_CATALOGUE, line.encode()))
    assert problems == [f"contains an ISIN; {check_hygiene.ISIN_RULE}"]


def test_isins_outside_config_and_data_pass() -> None:
    content = f"PUBLIC_EXAMPLE_ISIN = '{PUBLIC_EXAMPLE_ISIN}'\n".encode()
    assert list(check_hygiene.content_problems("tests/test_x.py", content)) == []


def test_oversized_files_are_flagged() -> None:
    content = b"x" * (check_hygiene.MAX_FILE_BYTES + 1)
    assert list(check_hygiene.content_problems("big.txt", content)) == [
        f"file is larger than {check_hygiene.MAX_FILE_BYTES:,} bytes"
    ]


def test_binary_content_is_flagged_unless_it_is_a_screenshot() -> None:
    [problem] = check_hygiene.content_problems("docs/report.bin", b"\x00\x01binary")
    assert problem.startswith("binary content")
    assert list(check_hygiene.content_problems("docs/img/home.png", png())) == []


def test_blocked_formats_are_reported_once() -> None:
    path = "data/prices.xlsx"
    content = b"PK\x03\x04\x00binary"
    problems = [*check_hygiene.path_problems(path), *check_hygiene.content_problems(path, content)]
    assert problems == [BLOCKED_FORMAT]


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        (png(), None),
        (png(png_chunk(b"tEXt", b"Author\x00Someone")), "metadata"),
        (png(png_chunk(b"eXIf", b"MM\x00*")), "metadata"),
        (b"PK\x03\x04 an archive", "not a PNG file"),
        (png()[:20], "incomplete"),
    ],
)
def test_screenshots_must_be_pngs_without_metadata(content: bytes, problem: str | None) -> None:
    problems = list(check_hygiene.content_problems("docs/img/home.png", content))
    if problem is None:
        assert problems == []
    else:
        assert len(problems) == 1
        assert problem in problems[0]


def test_force_added_private_files_are_caught(
    repo: Path, run_git: GitRunner, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "private").mkdir()
    (repo / "private" / "brief.md").write_text("notes\n", encoding="utf-8")
    run_git("add", "-f", "private/brief.md")

    assert check_hygiene.main([]) == EXIT_PROBLEMS
    assert capsys.readouterr().err == f"hygiene: private/brief.md: {PRIVATE}\n"


def test_clean_repository_passes(repo: Path, run_git: GitRunner) -> None:
    (repo / "README.md").write_text("Hello\n", encoding="utf-8")
    run_git("add", "README.md")

    assert check_hygiene.main([]) == EXIT_CLEAN


@pytest.mark.parametrize(
    "path",
    [
        *(f"example{suffix}" for suffix in sorted(BLOCKED_SUFFIXES)),
        "store.db-wal",
        "store.sqlite-journal",
        "private/notes.md",
        "docs/private/notes.md",
        "local/store.db",
        "CLAUDE.local.md",
        ".claude/settings.local.json",
        ".streamlit/secrets.toml",
        ".env",
        "denylist.txt",
    ],
)
def test_gitignore_ignores_what_the_policy_blocks(
    repo: Path, run_git: GitRunner, path: str
) -> None:
    shutil.copy(PROJECT_ROOT / ".gitignore", repo / ".gitignore")

    assert run_git("check-ignore", "--no-index", path).strip() == path
