from pathlib import Path

import pytest

from tests.tools.sentinels import GitRunner
from tools._git import changed_files, decode_text, index_files, read_objects, tracked_files


@pytest.mark.parametrize("content", [b"text\x00with a null byte", b"\xff\xfe not utf-8"])
def test_binary_content_is_not_decoded(content: bytes) -> None:
    assert decode_text(content) is None


def test_utf8_text_is_decoded() -> None:
    assert decode_text("Pound sign: £".encode()) == "Pound sign: £"


def test_index_files_lists_staged_files_with_their_content_ids(
    repo: Path, run_git: GitRunner
) -> None:
    (repo / "a b.txt").write_text("hello\n", encoding="utf-8")
    run_git("add", "a b.txt")

    [file] = index_files(repo)

    assert (file.path, file.mode) == ("a b.txt", "100644")
    assert read_objects([file.object_id], cwd=repo) == {file.object_id: b"hello\n"}
    assert tracked_files(repo) == ["a b.txt"]


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
