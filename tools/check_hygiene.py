"""Repository hygiene: what must never be tracked, whatever ``.gitignore`` says.

Checks every file in the git index (staged additions included):

* nothing under ``private/`` or ``local/``, and no private notes or local settings;
* no binary data formats such as spreadsheets, databases or notebooks;
* images only in the reviewed screenshots directory, as real PNG files without metadata;
* no file larger than a sensible limit;
* no valid ISIN (a fund or share identifier) in ``config/`` or ``data/``, where only asset-class
  proxies and demo instruments belong.

Usage::

    python -m tools.check_hygiene
"""

import argparse
import re
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path, PurePosixPath

from tools._git import StoredFile, index_files, read_objects, repo_root
from tools._report import Problem, report
from tools._text import decode_text
from tools.policy import (
    BLOCKED_FORMAT,
    BLOCKED_SUFFIXES,
    IMAGE_DIRECTORY,
    IMAGE_SUFFIXES,
    PRIVATE_FILES,
    PRIVATE_PREFIXES,
    is_screenshot_path,
    screenshot_problem,
)

MAX_FILE_BYTES = 1_000_000
ISIN_DIRECTORIES = ("config/", "data/")
LUHN_DOUBLED_DIGIT_LIMIT = 9
LUHN_MODULUS = 10
ALPHANUMERIC_BASE = 36

_ISIN_SHAPE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b")


def is_valid_isin(candidate: str) -> bool:
    """Return whether an ISIN-shaped string has a valid check digit.

    Letters become two-digit numbers (A is 10, Z is 35), then the Luhn checksum is applied to the
    resulting digit string, check digit included.
    """
    digits = "".join(str(int(character, ALPHANUMERIC_BASE)) for character in candidate)
    total = 0
    for position, digit in enumerate(int(character) for character in reversed(digits)):
        value = digit * 2 if position % 2 else digit
        total += value - LUHN_DOUBLED_DIGIT_LIMIT if value > LUHN_DOUBLED_DIGIT_LIMIT else value
    return total % LUHN_MODULUS == 0


def path_problems(path: str) -> Iterator[str]:
    """Yield the policy problems with a tracked path, judged by its name alone."""
    suffix = PurePosixPath(path).suffix.lower()
    if path.startswith(PRIVATE_PREFIXES) or path in PRIVATE_FILES:
        yield "private or local file is tracked"
    if suffix in BLOCKED_SUFFIXES:
        yield BLOCKED_FORMAT
    if suffix in IMAGE_SUFFIXES and not path.startswith(IMAGE_DIRECTORY):
        yield f"images belong in {IMAGE_DIRECTORY} after review"


def content_problems(path: str, content: bytes) -> Iterator[str]:
    """Yield the policy problems with a tracked file's content."""
    if len(content) > MAX_FILE_BYTES:
        yield f"file is larger than {MAX_FILE_BYTES:,} bytes"
    if is_screenshot_path(path) and (problem := screenshot_problem(content)) is not None:
        yield problem
    text = decode_text(content) if path.startswith(ISIN_DIRECTORIES) else None
    if text is not None and any(is_valid_isin(match) for match in _ISIN_SHAPE.findall(text)):
        yield "contains an ISIN; config and data hold only asset-class proxies and demo instruments"


def check_repository(root: Path, files: Sequence[StoredFile]) -> list[Problem]:
    """Check every tracked file, reading content from the git index."""
    contents = read_objects((file.object_id for file in files if not file.is_submodule), cwd=root)
    problems: list[Problem] = []
    for file in files:
        content = contents.get(file.object_id, b"")
        messages = [*path_problems(file.path), *content_problems(file.path, content)]
        problems.extend(Problem(file.path, message) for message in messages)
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    """Run the check and return a process exit code (0 clean, 1 problems found)."""
    argparse.ArgumentParser(
        description="Check that nothing private, binary or oversized is tracked."
    ).parse_args(argv)
    root = repo_root()
    return report("hygiene", check_repository(root, index_files(root)))


if __name__ == "__main__":
    sys.exit(main())
