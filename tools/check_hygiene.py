"""Repository hygiene: what must never be tracked, whatever ``.gitignore`` says.

Checks every file in the git index (staged additions included):

* nothing in a ``private/`` or ``local/`` directory at any depth, and no private notes, local
  settings, secrets or denylist;
* no data or document formats such as spreadsheets, databases, notebooks or PDFs, nor their
  journal files;
* no other binary content except reviewed screenshots, which must be PNG files in ``docs/img/``
  without metadata;
* no file larger than a sensible limit;
* no valid ISIN (a fund or share identifier) in the names or content of files in ``config/`` or
  ``data/``, where only asset-class proxies and demo instruments belong.

CI runs this check on every push, so it is the public backstop for anything the local hooks miss.

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
    FUND_CATALOGUE,
    IMAGE_DIRECTORY,
    IMAGE_SUFFIXES,
    REFERENCE_DATA_DIRECTORY,
    is_blocked_format,
    is_private_path,
    is_screenshot_path,
    screenshot_problem,
)

MAX_FILE_BYTES = 1_000_000
ISIN_PATHS = ("config/", "data/", REFERENCE_DATA_DIRECTORY, FUND_CATALOGUE)
"""Where ISINs are refused: configuration, data and the fund list."""
LUHN_DOUBLED_DIGIT_LIMIT = 9
LUHN_MODULUS = 10
ALPHANUMERIC_BASE = 36

_ISIN_SHAPE = re.compile(r"(?<![A-Za-z0-9])[A-Z]{2}[A-Z0-9]{9}[0-9](?![A-Za-z0-9])")
"""Two letters, nine letters or digits, and a check digit, with no letter or digit either side.

Underscores count as a boundary, so ``isin_US0378331005`` is caught. ISINs are upper case, and a
case-insensitive search would mistake names such as ``portfolio005`` for one.
"""
ISIN_RULE = "config and data name a fund only by its name and ticker"


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


def contains_isin(text: str) -> bool:
    """Whether the text holds an ISIN-shaped string with a valid check digit."""
    return any(is_valid_isin(match) for match in _ISIN_SHAPE.findall(text))


def path_problems(path: str) -> Iterator[str]:
    """Yield the policy problems with a tracked path, judged by its name alone."""
    if is_private_path(path):
        yield "private or local file is tracked"
    if is_blocked_format(path):
        yield BLOCKED_FORMAT
    is_image = PurePosixPath(path).suffix.lower() in IMAGE_SUFFIXES
    if is_image and not path.startswith(IMAGE_DIRECTORY):
        yield f"images belong in {IMAGE_DIRECTORY} after review"
    if path.startswith(ISIN_PATHS) and contains_isin(path):
        yield f"file name contains an ISIN; {ISIN_RULE}"


def content_problems(path: str, content: bytes) -> Iterator[str]:
    """Yield the policy problems with a tracked file's content."""
    if len(content) > MAX_FILE_BYTES:
        yield f"file is larger than {MAX_FILE_BYTES:,} bytes"
    if is_blocked_format(path):
        return
    if is_screenshot_path(path):
        if (problem := screenshot_problem(content)) is not None:
            yield problem
        return
    text = decode_text(content)
    if text is None:
        yield f"binary content; only screenshots in {IMAGE_DIRECTORY} may be binary"
    elif path.startswith(ISIN_PATHS) and contains_isin(text):
        yield f"contains an ISIN; {ISIN_RULE}"


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
