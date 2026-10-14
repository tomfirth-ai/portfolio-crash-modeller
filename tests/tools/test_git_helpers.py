from pathlib import Path

import pytest

from tests.tools.helpers import GitRunner
from tools._git import GitError, changed_files, git, index_files, read_objects


def test_index_files_lists_staged_files_with_their_content_ids(
    repo: Path, run_git: GitRunner
) -> None:
    (repo / "a b.txt").write_text("hello\n", encoding="utf-8")
    run_git("add", "a b.txt")

    [file] = index_files(repo)

    assert (file.path, file.mode) == ("a b.txt", "100644")
    assert read_objects([file.object_id], cwd=repo) == {file.object_id: b"hello\n"}


def test_changed_files_parses_raw_diff_output() -> None:
    raw = (
        b":000000 100644 " + b"0" * 40 + b" " + b"a" * 40 + b" A\0new.txt\0"
        b":100644 120000 " + b"b" * 40 + b" " + b"c" * 40 + b" T\0link\0"
    )

    assert [(file.path, file.mode, file.object_id) for file in changed_files(raw)] == [
        ("new.txt", "100644", "a" * 40),
        ("link", "120000", "c" * 40),
    ]


def test_reading_a_missing_object_fails(repo: Path) -> None:
    with pytest.raises(LookupError, match="missing"):
        read_objects(["1" * 40], cwd=repo)


def test_git_errors_include_what_git_said(tmp_path: Path) -> None:
    with pytest.raises(GitError, match="not a git repository"):
        git("rev-parse", "--show-toplevel", cwd=tmp_path)
