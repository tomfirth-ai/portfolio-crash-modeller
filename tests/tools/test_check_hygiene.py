from pathlib import Path

import pytest

from tests.tools.sentinels import GitRunner
from tools import check_hygiene

PUBLIC_EXAMPLE_ISIN = "US0378331005"
"""A well-known, public ISIN with a valid check digit, used only as test data."""


def test_isin_check_digit_is_validated() -> None:
    assert check_hygiene.is_valid_isin(PUBLIC_EXAMPLE_ISIN)
    assert not check_hygiene.is_valid_isin("US0378331006")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("private/notes.md", "private or local file is tracked"),
        ("local/crashmodel.db", "private or local file is tracked"),
        ("CLAUDE.local.md", "private or local file is tracked"),
        ("data/prices.xlsx", "binary data formats are never committed"),
        ("screenshot.png", "images belong in docs/img/ after review"),
    ],
)
def test_path_problems(path: str, expected: str) -> None:
    assert expected in list(check_hygiene.path_problems(path))


@pytest.mark.parametrize("path", ["docs/img/home.png", "src/crashmodel/__init__.py", "README.md"])
def test_allowed_paths_pass(path: str) -> None:
    assert list(check_hygiene.path_problems(path)) == []


def test_valid_isins_in_config_are_flagged() -> None:
    content = f"instrument: {PUBLIC_EXAMPLE_ISIN}\n".encode()
    assert list(check_hygiene.content_problems("config/demo.yaml", content))


def test_isin_shaped_strings_with_bad_check_digits_pass() -> None:
    assert list(check_hygiene.content_problems("config/demo.yaml", b"id: US0378331006\n")) == []


def test_isins_outside_config_and_data_pass() -> None:
    content = f"PUBLIC_EXAMPLE_ISIN = '{PUBLIC_EXAMPLE_ISIN}'\n".encode()
    assert list(check_hygiene.content_problems("tests/test_x.py", content)) == []


def test_oversized_files_are_flagged() -> None:
    content = b"x" * (check_hygiene.MAX_FILE_BYTES + 1)
    assert list(check_hygiene.content_problems("big.txt", content))


def test_force_added_private_files_are_caught(repo: Path, run_git: GitRunner) -> None:
    (repo / "private").mkdir()
    (repo / "private" / "brief.md").write_text("notes\n", encoding="utf-8")
    run_git("add", "-f", "private/brief.md")

    assert check_hygiene.main() == 1


def test_clean_repository_passes(repo: Path, run_git: GitRunner) -> None:
    (repo / "README.md").write_text("Hello\n", encoding="utf-8")
    run_git("add", "README.md")

    assert check_hygiene.main() == 0
