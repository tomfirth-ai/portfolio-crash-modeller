"""Thin helpers for running git from the guard tools."""

import os
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

SUBMODULE_MODE = "160000"
"""The mode git records for a submodule, whose content lives in another repository."""


@dataclass(frozen=True)
class StoredFile:
    """A file as git stores it, in the index or in a commit.

    Attributes:
        path: Path from the repository root.
        mode: Git file mode, such as ``100644`` for a file or ``120000`` for a symbolic link.
        object_id: Id of the git object that holds the file's content.
    """

    path: str
    mode: str
    object_id: str

    @property
    def is_submodule(self) -> bool:
        """Whether the entry is a submodule, which has no content in this repository."""
        return self.mode == SUBMODULE_MODE


def git(*args: str, cwd: Path | None = None, stdin: bytes | None = None) -> bytes:
    """Run a git command and return its standard output.

    Args:
        *args: Arguments passed to git.
        cwd: Directory to run in. Defaults to the current directory.
        stdin: Bytes to send to git's standard input.

    Returns:
        The raw standard output.

    Raises:
        subprocess.CalledProcessError: If git exits with a non-zero status.
    """
    return subprocess.run(
        ["git", *args], cwd=cwd, input=stdin, capture_output=True, check=True
    ).stdout


def repo_root(cwd: Path | None = None) -> Path:
    """Return the top-level directory of the enclosing git repository."""
    return Path(git("rev-parse", "--show-toplevel", cwd=cwd).decode().strip())


def tracked_files(cwd: Path | None = None) -> list[str]:
    """Return the paths of every file in the git index, staged additions included."""
    return [file.path for file in index_files(cwd)]


def index_files(cwd: Path | None = None) -> list[StoredFile]:
    """Return every file in the git index, staged additions included."""
    files: list[StoredFile] = []
    for record in filter(None, git("ls-files", "--stage", "-z", cwd=cwd).split(b"\0")):
        details, _, path = record.partition(b"\t")
        mode, object_id, _stage = details.decode().split()
        files.append(StoredFile(os.fsdecode(path), mode, object_id))
    return files


def changed_files(raw_diff: bytes) -> list[StoredFile]:
    """Parse ``--raw -z --no-renames`` diff output into the new version of each changed file.

    Callers exclude deletions with ``--diff-filter=d``, because a deleted file has no new version.
    """
    fields = raw_diff.split(b"\0")
    files: list[StoredFile] = []
    for details, path in zip(fields[0::2], fields[1::2], strict=False):
        _old_mode, mode, _old_id, object_id, _status = details.decode().lstrip(":").split()
        files.append(StoredFile(os.fsdecode(path), mode, object_id))
    return files


def read_objects(object_ids: Iterable[str], cwd: Path | None = None) -> dict[str, bytes]:
    """Read git objects by id, all in one git process.

    ``git cat-file --batch`` returns exactly the bytes git stores and will push, so attributes,
    text conversion drivers and log settings cannot hide or rewrite anything.

    Raises:
        LookupError: If an object is missing from the repository.
    """
    wanted = list(dict.fromkeys(object_ids))
    if not wanted:
        return {}
    request = "".join(f"{object_id}\n" for object_id in wanted).encode()
    output = git("cat-file", "--batch", cwd=cwd, stdin=request)
    objects: dict[str, bytes] = {}
    position = 0
    for object_id in wanted:
        header_end = output.index(b"\n", position)
        header = output[position:header_end]
        if header.endswith(b" missing"):
            raise LookupError(f"git object {object_id} is missing")
        start, size = header_end + 1, int(header.rsplit(b" ", 1)[1])
        objects[object_id] = output[start : start + size]
        position = start + size + 1
    return objects


def decode_text(content: bytes) -> str | None:
    """Decode file content as UTF-8 text, or return ``None`` if it looks binary."""
    if b"\0" in content:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None
