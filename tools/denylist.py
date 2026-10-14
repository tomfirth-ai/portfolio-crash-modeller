"""The privacy denylist: loading it, and finding its entries in text.

The denylist is a private file, written by hand, that lists personal details which must never
reach the repository: names, tickers, amounts, dates. It lives outside the repository, and nothing
in this module reveals what it holds.

Matching is forgiving, so that small changes of form do not slip through:

* words are compared as sequences of tokens, after splitting on spaces, punctuation,
  ``snake_case`` and ``camelCase`` and ignoring case and accents. ``Jane Doe``, ``jane_doe``,
  ``janeDoe``, ``JANEDOE`` and a ``Jane`` at the end of one line with ``Doe`` starting the next all
  match ``Jane Doe``, while a short entry never matches inside a longer word;
* a two-word name also matches in reverse order (``Doe, Jane``) and with initials between the
  words (``Jane Q. Doe``);
* amounts are compared by value, so ``271828`` also matches ``271,828``, ``271828.00``, the same
  amount in pence and the same amount divided by 100;
* ISO dates such as ``2031-02-17`` also match the common UK, US and long-form spellings.
"""

import re
import subprocess
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from tools._git import git

GIT_CONFIG_KEY = "crashmodel.denylist"
"""Git setting that overrides the default denylist location."""
DEFAULT_LOCATION = Path("~/.config/crashmodel/denylist.txt")

MIN_DISTINCTIVE_DIGITS = 4
"""Rounded or rescaled amounts with fewer digits than this are too common to match safely."""
MIN_DISTINCTIVE_CHARACTERS = 3
"""Word entries shorter than this are matched, but trigger a false-positive warning."""
MAX_INITIALS = 2
"""Single letters allowed between the two words of a name, as in ``Jane Q. Doe``."""
NAME_WORDS = 2
"""Names of exactly this many words also match in reverse order, as in ``Doe, Jane``."""
PENCE_PER_POUND = Decimal(100)
DECIMAL_PLACES_TO_ROUND = (1, 2)

MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

_IGNORED_CATEGORIES = frozenset({"Mn", "Cf"})
"""Accents left over from decomposition, and invisible format characters such as soft hyphens."""

_WORD_OR_NUMBER_RUN = re.compile(r"[^\W\d_]+|\d+")
_CASE_BOUNDARY = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_AMOUNT_ENTRY = re.compile(r"[£$€]?\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*p?", re.IGNORECASE)
_AMOUNT_IN_TEXT = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
_ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


class DenylistError(Exception):
    """The denylist is missing, empty or in an unsafe place."""


@dataclass(frozen=True)
class Entry:
    """One denylist entry, prepared for matching.

    Attributes:
        line: Line number of the entry in the denylist file, used to report matches.
        sequences: Token sequences that count as a match.
        amounts: Numeric values that count as a match, for entries that are amounts.
        is_name: Whether the entry is a two-word name, which may have initials between its words.
    """

    line: int
    sequences: tuple[tuple[str, ...], ...]
    amounts: frozenset[Decimal] = field(default_factory=frozenset)
    is_name: bool = False

    @property
    def is_short(self) -> bool:
        """Whether the entry is so short that it may cause false positives."""
        longest = max((len("".join(sequence)) for sequence in self.sequences), default=0)
        return longest < MIN_DISTINCTIVE_CHARACTERS


type Candidate = tuple[tuple[str, ...], Entry]
"""A token sequence to look for, and the entry it belongs to."""


def tokenise(text: str) -> tuple[str, ...]:
    """Split text into lower-case word and number tokens, ignoring accents.

    Splits on anything that is not a letter or digit, between letters and digits, and at
    ``camelCase`` boundaries. Compatibility decomposition (NFKD) first turns lookalike characters
    into their plain forms; accents and invisible format characters are then dropped.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) not in _IGNORED_CATEGORIES
    )
    tokens: list[str] = []
    for run in _WORD_OR_NUMBER_RUN.findall(plain):
        tokens.extend(part.casefold() for part in _CASE_BOUNDARY.split(run) if part)
    return tuple(tokens)


def parse_amount(raw: str) -> Decimal | None:
    """Parse an entry such as ``£271,828.00`` or ``2718p`` as a number, or return ``None``."""
    match = _AMOUNT_ENTRY.fullmatch(raw.strip())
    if match is None:
        return None
    whole, fraction = match.groups()
    return Decimal(whole.replace(",", "") + (fraction or ""))


def _digit_count(value: Decimal) -> int:
    return len(format(value, "f").replace(".", "").replace("-", "").lstrip("0"))


def _decimal_places(value: Decimal) -> int:
    exponent = value.as_tuple().exponent
    return -exponent if isinstance(exponent, int) and exponent < 0 else 0


def amount_variants(value: Decimal) -> frozenset[Decimal]:
    """Return the values an amount may appear as: itself, rounded, in pence, or divided by 100.

    Variants other than the value itself are kept only when they still have enough digits to be
    distinctive, so a rounded figure such as ``68`` does not match every 68 in the code base.
    """
    variants = {value * PENCE_PER_POUND, value / PENCE_PER_POUND}
    variants |= {
        value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        for places in DECIMAL_PLACES_TO_ROUND
        if _decimal_places(value) > places
    }
    distinctive = {
        variant for variant in variants if _digit_count(variant) >= MIN_DISTINCTIVE_DIGITS
    }
    return frozenset(variant.normalize() for variant in {value, *distinctive})


def amounts_in(text: str) -> frozenset[Decimal]:
    """Return every number written in the text, normalised for comparison by value."""
    return frozenset(
        Decimal(match.replace(",", "")).normalize() for match in _AMOUNT_IN_TEXT.findall(text)
    )


def date_spellings(day: date) -> tuple[str, ...]:
    """Return the common ways a date is written, in ISO, UK, US and long forms."""
    month = MONTH_NAMES[day.month - 1]
    return (
        day.isoformat(),
        f"{day:%Y%m%d}",
        f"{day:%d/%m/%Y}",
        f"{day.day}/{day.month}/{day.year}",
        f"{day:%m/%d/%Y}",
        f"{day.month}/{day.day}/{day.year}",
        f"{day.day} {month} {day.year}",
        f"{day.day} {month[:3]} {day.year}",
        f"{month} {day.day}, {day.year}",
        f"{month[:3]} {day.day}, {day.year}",
    )


def _is_name(tokens: tuple[str, ...]) -> bool:
    return len(tokens) == NAME_WORDS and all(token.isalpha() for token in tokens)


def _word_sequences(tokens: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    """Return the token sequences that count as the words of an entry.

    Words written together, as in an e-mail address or a constant (``JANEDOE``), form a single
    token, so a multi-word entry also matches its words joined up. A two-word name also matches
    in reverse order.
    """
    sequences = [tokens]
    if len(tokens) > 1:
        sequences.append(("".join(tokens),))
    if _is_name(tokens):
        sequences.append(tokens[::-1])
    return tuple(sequences)


def parse_entry(line: int, raw: str) -> Entry:
    """Prepare one denylist line for matching, treating amounts and ISO dates specially."""
    text = raw.strip()
    if (amount := parse_amount(text)) is not None:
        plain = format(amount.normalize(), "f")
        return Entry(line, sequences=(tokenise(plain),), amounts=amount_variants(amount))
    if (iso := _ISO_DATE.fullmatch(text)) is not None:
        day = date(*(int(part) for part in iso.groups()))
        return Entry(line, sequences=tuple(tokenise(spelling) for spelling in date_spellings(day)))
    tokens = tokenise(text)
    return Entry(line, sequences=_word_sequences(tokens), is_name=_is_name(tokens))


def load_denylist(path: Path, repository: Path) -> list[Entry]:
    """Load and prepare the denylist, failing closed on anything unsafe.

    Args:
        path: Location of the denylist file.
        repository: Root of the repository being protected.

    Returns:
        The prepared entries, one per non-blank, non-comment line.

    Raises:
        DenylistError: If the file is inside the repository, missing, or has no entries.
    """
    resolved = path.expanduser().resolve()
    if resolved.is_relative_to(repository.resolve()):
        raise DenylistError("the denylist must live outside the repository")
    if not resolved.is_file():
        raise DenylistError(f"no denylist found at {resolved}")
    entries = [
        parse_entry(number, line)
        for number, line in enumerate(resolved.read_text(encoding="utf-8").splitlines(), start=1)
        if line.strip() and not line.lstrip().startswith("#")
    ]
    entries = [entry for entry in entries if any(entry.sequences)]
    if not entries:
        raise DenylistError("the denylist has no entries")
    return entries


def configured_denylist_path(repository: Path) -> Path:
    """Return the denylist path from ``git config crashmodel.denylist``, or the default location."""
    try:
        configured = git("config", "--get", GIT_CONFIG_KEY, cwd=repository).decode().strip()
    except subprocess.CalledProcessError:
        configured = ""
    return Path(configured) if configured else DEFAULT_LOCATION.expanduser()


class Matcher:
    """Finds denylist entries in text.

    Entries are indexed by their first token and by their amounts, so a scan costs roughly one
    dictionary lookup per token and per number, however long the denylist.
    """

    def __init__(self, entries: Sequence[Entry]) -> None:
        """Index the entries for matching."""
        self._by_first_token: defaultdict[str, list[Candidate]] = defaultdict(list)
        self._by_amount: defaultdict[Decimal, list[Entry]] = defaultdict(list)
        for entry in entries:
            for sequence in entry.sequences:
                if sequence:
                    self._by_first_token[sequence[0]].append((sequence, entry))
            for amount in entry.amounts:
                self._by_amount[amount].append(entry)

    def find(self, text: str) -> list[tuple[int, Entry]]:
        """Return each ``(line number, entry)`` match in the text, in order and without repeats.

        Words are matched across line breaks, and reported on the line where the match starts.
        """
        tokens: list[str] = []
        token_lines: list[int] = []
        matches: dict[tuple[int, int], Entry] = {}
        for number, line in enumerate(text.splitlines(), start=1):
            line_tokens = tokenise(line)
            tokens.extend(line_tokens)
            token_lines.extend([number] * len(line_tokens))
            for amount in amounts_in(line):
                for entry in self._by_amount.get(amount, ()):
                    matches.setdefault((number, entry.line), entry)
        for start, token in enumerate(tokens):
            for sequence, entry in self._by_first_token.get(token, ()):
                if _occurs_at(tokens, start, sequence, MAX_INITIALS if entry.is_name else 0):
                    matches.setdefault((token_lines[start], entry.line), entry)
        return [(line, matches[line, entry_line]) for line, entry_line in sorted(matches)]

    def entries_in(self, text: str) -> list[Entry]:
        """Return the entries found anywhere in the text, in denylist order, without repeats."""
        found = {entry.line: entry for _, entry in self.find(text)}
        return [found[line] for line in sorted(found)]


def _occurs_at(tokens: Sequence[str], start: int, sequence: Sequence[str], gap: int) -> bool:
    """Return whether ``sequence`` occurs in ``tokens`` from ``start``.

    Up to ``gap`` single-letter tokens, such as initials, may sit between consecutive words.
    """
    position = start
    for index, word in enumerate(sequence):
        if index:
            skipped = 0
            while (
                skipped < gap
                and position < len(tokens)
                and len(tokens[position]) == 1
                and tokens[position] != word
            ):
                position += 1
                skipped += 1
        if position >= len(tokens) or tokens[position] != word:
            return False
        position += 1
    return True
