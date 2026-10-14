"""Style check: no dash lookalikes anywhere, and British spelling in prose.

The project writes British English and never uses en or em dashes. This check enforces both:

* every tracked text file, and every commit message, is checked for en and em dashes and their
  lookalikes, such as the Unicode minus sign and the non-breaking hyphen;
* Markdown prose and commit messages are checked for common American spellings. Code blocks, inline
  code and links are ignored, because code often has to use American identifiers such as ``color``.

Usage::

    python -m tools.check_style [FILE ...]      # default: every tracked file
    python -m tools.check_style --message FILE  # commit-msg hook
"""

import argparse
import re
import sys
import unicodedata
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from tools._git import decode_text, tracked_files

DASH_LOOKALIKES = frozenset(
    chr(code)
    for code in (
        0x2010,  # hyphen
        0x2011,  # non-breaking hyphen
        0x2012,  # figure dash
        0x2013,  # en dash
        0x2014,  # em dash
        0x2015,  # horizontal bar
        0x2212,  # minus sign
        0x2E3A,  # two-em dash
        0x2E3B,  # three-em dash
        0xFE58,  # small em dash
        0xFE63,  # small hyphen-minus
        0xFF0D,  # fullwidth hyphen-minus
    )
)
"""Characters that read as a dash. Use a hyphen, a comma, "to" or a new sentence instead."""

AMERICAN_SPELLINGS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), british)
    for pattern, british in (
        (r"\bcolor(?:s|ed|ing|ful)?\b", "colour"),
        (r"\bbehaviors?\b", "behaviour"),
        (r"\bfavor(?:s|ed|ing|ite|ites)?\b", "favour"),
        (r"\banalyz(?:e|es|ed|ing)\b", "analyse"),
        (r"\borganiz(?:e|es|ed|ing|ation|ations)\b", "organise"),
        (r"\boptimiz(?:e|es|ed|ing|ation|ations)\b", "optimise"),
        (r"\bsummariz(?:e|es|ed|ing)\b", "summarise"),
        (r"\brealiz(?:e|es|ed|ing)\b", "realise"),
        (r"\bprioritiz(?:e|es|ed|ing)\b", "prioritise"),
        (r"\bvisualiz(?:e|es|ed|ing|ation|ations)\b", "visualise"),
        (r"\bmodel(?:ing|ed|er|ers)\b", "modelling, modelled or modeller"),
        (r"\blabel(?:ed|ing)\b", "labelled or labelling"),
        (r"\bcancel(?:ed|ing)\b", "cancelled or cancelling"),
        (r"\bcenter(?:s|ed)?\b", "centre"),
        (r"\bgray\b", "grey"),
        (r"\bdefense\b", "defence"),
        (r"\bcatalogs?\b", "catalogue"),
    )
)
"""Common American spellings and their British forms."""

PROSE_SUFFIXES = frozenset({".md"})

_FENCED_CODE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_LINK_TARGET = re.compile(r"\]\([^)]*\)|https?://\S+")


@dataclass(frozen=True)
class Problem:
    """A style problem at a position in a file."""

    location: str
    line: int
    message: str

    def __str__(self) -> str:
        """Format the problem as ``location:line: message``."""
        return f"{self.location}:{self.line}: {self.message}"


def _blank(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def prose_only(markdown: str) -> str:
    """Blank out code blocks, inline code and link targets, keeping line numbers intact."""
    for pattern in (_FENCED_CODE, _INLINE_CODE, _LINK_TARGET):
        markdown = pattern.sub(_blank, markdown)
    return markdown


def find_dash_lookalikes(text: str, location: str) -> Iterator[Problem]:
    """Yield a problem for every dash lookalike in the text."""
    for number, line in enumerate(text.splitlines(), start=1):
        for character in sorted(set(line) & DASH_LOOKALIKES):
            name = unicodedata.name(character).lower()
            yield Problem(location, number, f"{name} found; use a hyphen, a comma or 'to'")


def find_american_spellings(text: str, location: str) -> Iterator[Problem]:
    """Yield a problem for every common American spelling in prose."""
    for number, line in enumerate(prose_only(text).splitlines(), start=1):
        for pattern, british in AMERICAN_SPELLINGS:
            for match in pattern.finditer(line):
                yield Problem(
                    location, number, f"American spelling '{match.group(0)}'; use {british}"
                )


def check_text(text: str, location: str, *, prose: bool) -> list[Problem]:
    """Check one text for dash lookalikes and, if it is prose, for American spellings."""
    problems = list(find_dash_lookalikes(text, location))
    if prose:
        problems.extend(find_american_spellings(text, location))
    return problems


def check_files(paths: Sequence[str]) -> list[Problem]:
    """Check files on disk, skipping any that are not UTF-8 text."""
    problems: list[Problem] = []
    for name in paths:
        text = decode_text(Path(name).read_bytes())
        if text is not None:
            problems.extend(check_text(text, name, prose=Path(name).suffix in PROSE_SUFFIXES))
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    """Run the check and return a process exit code (0 clean, 1 problems found)."""
    parser = argparse.ArgumentParser(description="Check for dash lookalikes and American spelling.")
    parser.add_argument("files", nargs="*", help="files to check (default: every tracked file)")
    parser.add_argument("--message", type=Path, metavar="FILE", help="check a commit message file")
    args = parser.parse_args(argv)
    if args.message is not None:
        problems = check_text(
            args.message.read_text(encoding="utf-8"), "commit message", prose=True
        )
    else:
        problems = check_files(args.files or tracked_files())
    for problem in problems:
        print(f"style: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
