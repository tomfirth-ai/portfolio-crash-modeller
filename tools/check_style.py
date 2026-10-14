"""Style check: no dash lookalikes anywhere, and British spelling in prose.

The project writes British English and never uses en or em dashes. This check enforces both:

* every tracked text file, and every commit message, is checked for en and em dashes and their
  lookalikes, such as the Unicode minus sign and the non-breaking hyphen;
* Markdown prose and commit messages are checked for common American spellings. Code blocks, inline
  code and links are ignored, because code often has to use American identifiers such as ``color``.
  In a commit message, git's comment lines and the diff added by ``git commit -v`` are ignored too.

Usage::

    python -m tools.check_style [FILE ...]      # default: every file in the git index
    python -m tools.check_style --message FILE  # commit-msg hook
"""

import argparse
import re
import sys
import unicodedata
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path

from tools._git import index_files, read_objects, repo_root, stored_commit_message
from tools._report import Problem, report
from tools._text import decode_text

DASH_LOOKALIKES = frozenset(
    chr(code)
    for code in (
        0x058A,  # armenian hyphen
        0x05BE,  # hebrew punctuation maqaf
        0x1400,  # canadian syllabics hyphen
        0x1806,  # mongolian todo soft hyphen
        0x2010,  # hyphen
        0x2011,  # non-breaking hyphen
        0x2012,  # figure dash
        0x2013,  # en dash
        0x2014,  # em dash
        0x2015,  # horizontal bar
        0x2212,  # minus sign
        0x2E17,  # double oblique hyphen
        0x2E1A,  # hyphen with diaeresis
        0x2E3A,  # two-em dash
        0x2E3B,  # three-em dash
        0x2E40,  # double hyphen
        0x2E5D,  # oblique hyphen
        0x301C,  # wave dash
        0x3030,  # wavy dash
        0x30A0,  # katakana-hiragana double hyphen
        0xFE31,  # presentation form for vertical em dash
        0xFE32,  # presentation form for vertical en dash
        0xFE58,  # small em dash
        0xFE63,  # small hyphen-minus
        0xFF0D,  # fullwidth hyphen-minus
        0x10EAD,  # yezidi hyphenation mark
    )
)
"""Characters that read as a dash: every Unicode dash punctuation mark except the hyphen-minus,
plus the minus sign. Use a hyphen, a comma, "to" or a new sentence instead."""


def _ise(match: re.Match[str]) -> str:
    return f"{match[1]}s{match[2]}"


def _our(match: re.Match[str]) -> str:
    return f"{match[1]}our{match[2] or ''}"


def _re(match: re.Match[str]) -> str:
    suffix = match[2] or ""
    return f"{match[1]}r{'e' if suffix in {'', 's'} else ''}{suffix}"


def _double_l(match: re.Match[str]) -> str:
    return f"{match[1]}l{match[2]}"


def _british_word(match: re.Match[str]) -> str:
    return f"{BRITISH_WORDS[match[1].lower()]}{match[2]}"


BRITISH_WORDS = {
    "catalog": "catalogue",
    "defense": "defence",
    "enrollment": "enrolment",
    "gray": "grey",
    "installment": "instalment",
    "offense": "offence",
}

AMERICAN_SPELLINGS: tuple[tuple[re.Pattern[str], Callable[[re.Match[str]], str]], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), british)
    for pattern, british in (
        # analyze, organization, optimizer, unrealized: -ise and -yse
        (r"\b(\w*?[iy])z(e|es|ed|ing|er|ers|ation|ations)\b", _ise),
        # color, colorblind, favorite, behavioral, neighborhood: -our
        (
            r"\b(\w*?(?:ard|arm|behavi|col|endeav|fav|flav|harb|hon|hum|lab|neighb|od|rig|rum|sav"
            r"|splend|vap|vig))or(s|ed|ing|al|ally|ful|less|ite|ites|able|ably|blind|hood)?\b",
            _our,
        ),
        # center, centered, fiber, theater: -re
        (r"\b(\w*?(?:calib|cent|fib|meag|sab|scept|somb|spect|theat))er(s|ed|ing)?\b", _re),
        # modeling, labeled, canceled, totaled: a doubled l
        (
            r"\b(\w*?(?:cancel|channel|counsel|equal|fuel|label|level|marvel|model|signal|total"
            r"|travel|tunnel))(ed|ing|er|ers)\b",
            _double_l,
        ),
        (rf"\b({'|'.join(BRITISH_WORDS)})(s?)\b", _british_word),
    )
)
"""Common American spelling patterns, each with a function that gives the British form."""

NOT_AMERICAN = frozenset(
    {
        *("size", "sizes", "sized", "sizing", "resize", "resizes", "resized", "resizing"),
        *("downsize", "downsized", "downsizing", "oversize", "oversized", "undersized"),
        *("prize", "prizes", "prized", "seize", "seizes", "seized", "seizing"),
        *("capsize", "capsized", "maize", "assize", "assizes"),
    }
)
"""Words the patterns catch that are spelt the same in British English."""

PROSE_SUFFIXES = frozenset({".md"})

_FENCED_CODE = re.compile(
    r"^[ \t]*(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^[ \t]*(?P=fence)(?:`*|~*)[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
"""A fenced code block, indented or not, closed by a fence at least as long as the opening one."""
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_LINK_TARGET = re.compile(r"\]\([^)]*\)|https?://\S+")


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
            yield Problem(location, f"{name} found; use a hyphen, a comma or 'to'", number)


def find_american_spellings(text: str, location: str) -> Iterator[Problem]:
    """Yield a problem for every common American spelling in prose."""
    for number, line in enumerate(prose_only(text).splitlines(), start=1):
        for pattern, british in AMERICAN_SPELLINGS:
            for match in pattern.finditer(line):
                if match[0].lower() not in NOT_AMERICAN:
                    message = f"American spelling '{match[0]}'; use {british(match).lower()}"
                    yield Problem(location, message, number)


def check_text(text: str, location: str, *, prose: bool) -> list[Problem]:
    """Check one text for dash lookalikes and, if it is prose, for American spellings."""
    problems = list(find_dash_lookalikes(text, location))
    if prose:
        problems.extend(find_american_spellings(text, location))
    return problems


def check_contents(contents: Mapping[str, bytes]) -> list[Problem]:
    """Check file contents by path, skipping any that are not UTF-8 text."""
    problems: list[Problem] = []
    for path, content in contents.items():
        text = decode_text(content)
        if text is not None:
            problems.extend(check_text(text, path, prose=Path(path).suffix in PROSE_SUFFIXES))
    return problems


def index_contents() -> dict[str, bytes]:
    """Return every file in the git index with its staged content."""
    root = repo_root()
    files = [file for file in index_files(root) if not file.is_submodule]
    objects = read_objects((file.object_id for file in files), cwd=root)
    return {file.path: objects[file.object_id] for file in files}


def check_message(draft: bytes) -> list[Problem]:
    """Check a draft commit message, as git will store it."""
    text = decode_text(draft)
    if text is None:
        return [Problem("commit message", "not UTF-8 text")]
    return check_text(stored_commit_message(text), "commit message", prose=True)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the check and return a process exit code (0 clean, 1 problems found)."""
    parser = argparse.ArgumentParser(description="Check for dash lookalikes and American spelling.")
    parser.add_argument("files", nargs="*", help="files to check (default: every tracked file)")
    parser.add_argument("--message", type=Path, metavar="FILE", help="check a commit message file")
    args = parser.parse_args(argv)
    if args.message is not None:
        problems = check_message(args.message.read_bytes())
    elif args.files:
        problems = check_contents({name: Path(name).read_bytes() for name in args.files})
    else:
        problems = check_contents(index_contents())
    return report("style", problems)


if __name__ == "__main__":
    sys.exit(main())
