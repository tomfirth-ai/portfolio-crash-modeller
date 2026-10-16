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
* amounts are compared by value, at the precision they are written. ``271828`` also matches
  ``271,828``, ``271_828``, ``271 828``, ``271828.37``, ``271,830``, ``£271.8k`` and ``272K``, and
  the same amount in pence or divided by 100. A figure has to keep four significant digits to
  count as a rounded or rescaled form, and four-digit whole numbers never do, because they are
  mostly years;
* ISO dates such as ``2031-02-17`` also match the common UK, US, code and long-form spellings,
  from ``17/02/31`` and ``date(2031, 2, 17)`` to ``February 17th, 2031``.
"""

import re
import subprocess
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from pathlib import Path

from tools._git import git

GIT_CONFIG_KEY = "crashmodel.denylist"
"""Git setting that overrides the default denylist location."""
DEFAULT_LOCATION = Path("~/.config/crashmodel/denylist.txt")

MIN_DISTINCTIVE_DIGITS = 4
"""Rounded or rescaled amounts with fewer significant digits are too common to match safely."""
ABBREVIATED_DIGITS = 3
"""Significant digits compared for an abbreviated amount such as ``£272k``."""
YEAR_LIKE = range(1000, 10000)
"""Four-digit whole numbers, mostly years, which never count as a rounded or rescaled amount."""
MAX_NUMBER_DIGITS = 18
"""Longer runs of digits are identifiers or hashes, not amounts."""
MIN_DISTINCTIVE_CHARACTERS = 3
"""Word entries shorter than this are matched, but trigger a false-positive warning."""
MAX_INITIALS = 2
"""Single letters allowed between the two words of a name, as in ``Jane Q. Doe``."""
NAME_WORDS = 2
"""Names of exactly this many words also match in reverse order, as in ``Doe, Jane``."""
PENCE_PER_POUND = Decimal(100)
ROUNDINGS = (ROUND_HALF_UP, ROUND_DOWN)
"""A figure may be rounded to the nearest unit or simply cut short."""
MULTIPLIERS = {"k": Decimal(10) ** 3, "m": Decimal(10) ** 6, "bn": Decimal(10) ** 9}

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

ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}
TEENS = range(11, 14)
"""The 11th, 12th and 13th, which take ``th`` whatever their last digit."""

_IGNORED_CATEGORIES = frozenset({"Mn", "Cf"})
"""Accents left over from decomposition, and invisible format characters such as soft hyphens."""

_WORD_OR_NUMBER_RUN = re.compile(r"[^\W\d_]+|\d+")
_CASE_BOUNDARY = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_AMOUNT_ENTRY = re.compile(r"[£$€]?\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*p?", re.IGNORECASE)
_PLAIN_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?")
_GROUPED_NUMBER = re.compile(
    r"(?<![0-9.])[0-9]{1,3}(?:[,_' \u00a0\u202f][0-9]{3})+(?:\.[0-9]+)?(?![0-9])"
)
"""A number with thousands separators: commas, underscores, apostrophes or spaces."""
_ABBREVIATED_NUMBER = re.compile(r"([0-9]+(?:\.[0-9]+)?) ?(k|m|bn)\b", re.IGNORECASE)
_THOUSANDS_SEPARATORS = re.compile(r"[,_' \u00a0\u202f]")
_ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_TICKER_ENTRY = re.compile(r"(?=[0-9]*[A-Za-z])[A-Za-z0-9]{3,5}")
"""A ticker such as ``CW8G``: a short code of letters and digits, with at least one letter."""
_INLINE_COMMENT = re.compile(r"\s#")


class DenylistError(Exception):
    """The denylist is missing, unreadable, malformed or in an unsafe place.

    Messages name the denylist line at fault but never repeat its content.
    """


@dataclass(frozen=True)
class AmountForms:
    """The values an amount may be written as.

    Attributes:
        exact: The amount itself, and in pence or divided by 100 when still distinctive.
        rounded: Those values rounded or cut short to fewer digits, while still distinctive.
        abbreviated: Those values to three significant digits, matched only against abbreviated
            text such as ``£272k``.
    """

    exact: frozenset[Decimal]
    rounded: frozenset[Decimal] = frozenset()
    abbreviated: frozenset[Decimal] = frozenset()


@dataclass(frozen=True)
class Entry:
    """One denylist entry, prepared for matching.

    Attributes:
        line: Line number of the entry in the denylist file, used to report matches.
        sequences: Token sequences that count as a match.
        amounts: The values that count as a match, for entries that are amounts.
        is_name: Whether the entry is a two-word name, which may have initials between its words.
        is_words: Whether the entry is only words, such as a name, or a ticker. Entries with other
            digits, such as amounts, dates, sort codes and reference numbers, are not.
    """

    line: int
    sequences: tuple[tuple[str, ...], ...]
    amounts: AmountForms | None = None
    is_name: bool = False
    is_words: bool = False

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


def significant_digits(value: Decimal) -> int:
    """Return the number of significant digits, ignoring trailing zeros: 271800 has four."""
    return len(value.normalize().as_tuple().digits)


def is_distinctive(value: Decimal) -> bool:
    """Whether a rounded or rescaled amount is unusual enough to match without false alarms."""
    if significant_digits(value) < MIN_DISTINCTIVE_DIGITS:
        return False
    return not (value == value.to_integral_value() and int(value) in YEAR_LIKE)


def _exponent(value: Decimal) -> int:
    exponent = value.as_tuple().exponent
    return exponent if isinstance(exponent, int) else 0


def _round(value: Decimal, exponent: int) -> set[Decimal]:
    quantum = Decimal(1).scaleb(exponent)
    return {value.quantize(quantum, rounding=rounding) for rounding in ROUNDINGS}


def _tidy(value: Decimal) -> Decimal:
    """Drop zeros after the decimal point, so ``31415.900`` is held at the precision ``31415.9``."""
    return value.quantize(Decimal(1)) if value == value.to_integral_value() else value.normalize()


def amount_forms(value: Decimal) -> AmountForms:
    """Return the values an amount may be written as: see ``AmountForms``.

    Derived values, such as ``68`` for ``68.50``, are kept only when they are distinctive, so a
    short figure does not match every number in the code base.
    """
    rescaled = {_tidy(value * PENCE_PER_POUND), _tidy(value / PENCE_PER_POUND)}
    exact = {value, *filter(is_distinctive, rescaled)}
    rounded = {
        form
        for figure in exact
        for exponent in range(_exponent(figure) + 1, figure.adjusted() - MIN_DISTINCTIVE_DIGITS + 2)
        for form in _round(figure, exponent)
        if is_distinctive(form)
    }
    abbreviated = {
        form
        for figure in exact
        if significant_digits(figure) > ABBREVIATED_DIGITS
        for form in _round(figure, figure.adjusted() - ABBREVIATED_DIGITS + 1)
    }
    return AmountForms(frozenset(exact), frozenset(rounded), frozenset(abbreviated))


def _number(written: str) -> Decimal | None:
    digits = _THOUSANDS_SEPARATORS.sub("", written)
    return Decimal(digits) if len(digits) <= MAX_NUMBER_DIGITS else None


def amounts_in(text: str) -> frozenset[Decimal]:
    """Return every number written in the text, with and without reading thousands separators.

    Both readings are kept because a comma may also separate fields: in ``2031,1,314.16`` the
    numbers are ``2031``, ``1`` and ``314.16``, not ``1,314.16``.
    """
    written = [*_PLAIN_NUMBER.findall(text), *_GROUPED_NUMBER.findall(text)]
    return frozenset(number for number in map(_number, written) if number is not None)


def abbreviated_amounts_in(text: str) -> frozenset[Decimal]:
    """Return every amount written with a suffix for thousands, millions or billions: ``£272k``."""
    amounts: set[Decimal] = set()
    for figure, suffix in _ABBREVIATED_NUMBER.findall(text):
        number = _number(figure)
        if number is not None:
            amounts.add(number * MULTIPLIERS[suffix.lower()])
    return frozenset(amounts)


def ordinal_suffix(day: int) -> str:
    """Return the ordinal suffix for a day of the month: ``st``, ``nd``, ``rd`` or ``th``."""
    if day in TEENS:
        return "th"
    return ORDINAL_SUFFIXES.get(day % 10, "th")


def month_spellings(month: int) -> tuple[str, ...]:
    """Return the ways a month is written: in full, in three letters and, for September, Sept."""
    name = MONTH_NAMES[month - 1]
    return (name, name[:3], "Sept") if name == "September" else (name, name[:3])


def date_spellings(day: date) -> tuple[str, ...]:
    """Return the common ways a date is written, in ISO, UK, US, code and long forms.

    The numeric forms cover zero-padded and unpadded numbers and two-digit years, and
    ``f"{year} {month} {day}"`` stands for every year-first form, including ``date(2031, 2, 17)``
    and ``2031-2-17``. The long forms cover each month spelling, with and without an ordinal.
    """
    numeric = (
        day.isoformat(),
        f"{day:%Y%m%d}",
        f"{day:%d%m%Y}",
        f"{day.year} {day.month} {day.day}",
        f"{day:%d/%m/%Y}",
        f"{day.day}/{day.month}/{day.year}",
        f"{day:%d/%m/%y}",
        f"{day.day}/{day.month}/{day:%y}",
        f"{day:%m/%d/%Y}",
        f"{day.month}/{day.day}/{day.year}",
        f"{day:%m/%d/%y}",
    )
    days = (str(day.day), f"{day.day}{ordinal_suffix(day.day)}")
    worded = tuple(
        spelling
        for month in month_spellings(day.month)
        for day_of_month in days
        for spelling in (
            f"{day_of_month} {month} {day.year}",
            f"{month} {day_of_month}, {day.year}",
        )
    )
    return numeric + worded


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
    """Prepare one denylist line for matching, treating amounts and ISO dates specially.

    Raises:
        DenylistError: If the line has a comment after the entry, looks like an ISO date that does
            not exist, or has no letters or digits to match.
    """
    text = raw.strip()
    if _INLINE_COMMENT.search(text):
        raise DenylistError(
            f"denylist line {line} has a comment after the entry; put comments on their own line"
        )
    if (amount := parse_amount(text)) is not None:
        plain = format(amount.normalize(), "f")
        return Entry(line, sequences=(tokenise(plain),), amounts=amount_forms(amount))
    if (iso := _ISO_DATE.fullmatch(text)) is not None:
        try:
            day = date(*(int(part) for part in iso.groups()))
        except ValueError:
            raise DenylistError(f"denylist line {line} is not a real date") from None
        return Entry(line, sequences=tuple(tokenise(spelling) for spelling in date_spellings(day)))
    tokens = tokenise(text)
    if not tokens:
        raise DenylistError(f"denylist line {line} has no letters or digits to match")
    is_words = all(token.isalpha() for token in tokens) or bool(_TICKER_ENTRY.fullmatch(text))
    return Entry(
        line, sequences=_word_sequences(tokens), is_name=_is_name(tokens), is_words=is_words
    )


def _is_inside(path: Path, directory: Path) -> bool:
    """Whether ``path`` is ``directory`` or lies beneath it.

    Compares files, not spellings, so a differently cased path on a case-insensitive disk is
    still recognised.
    """
    return directory.exists() and any(
        candidate.exists() and candidate.samefile(directory) for candidate in (path, *path.parents)
    )


def load_denylist(path: Path, repository: Path) -> list[Entry]:
    """Load and prepare the denylist, failing closed on anything unsafe.

    Args:
        path: Location of the denylist file.
        repository: Root of the repository being protected.

    Returns:
        The prepared entries, one per line that is neither blank nor a ``#`` comment.

    Raises:
        DenylistError: If the file is inside the repository, missing, unreadable, not UTF-8 text,
            has a malformed line or has no entries.
    """
    resolved = path.expanduser().resolve()
    if _is_inside(resolved, repository.resolve()):
        raise DenylistError("the denylist must live outside the repository")
    if not resolved.is_file():
        raise DenylistError(f"no denylist found at {resolved}")
    try:
        # utf-8-sig drops the byte order mark some editors add, which would hide the first entry.
        text = resolved.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise DenylistError("the denylist is not UTF-8 text") from None
    except OSError as error:
        raise DenylistError(f"cannot read the denylist: {error.strerror}") from None
    entries = [
        parse_entry(number, line)
        for number, line in enumerate(text.splitlines(), start=1)
        if line.strip() and not line.lstrip().startswith("#")
    ]
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

    Entries are indexed by their first token and by their amounts, so a scan costs a few
    dictionary lookups per token and per number, however long the denylist.
    """

    def __init__(self, entries: Sequence[Entry]) -> None:
        """Index the entries for matching."""
        self._by_first_token: defaultdict[str, list[Candidate]] = defaultdict(list)
        self._exact: defaultdict[Decimal, list[Entry]] = defaultdict(list)
        self._rounded: defaultdict[Decimal, list[Entry]] = defaultdict(list)
        self._abbreviated: defaultdict[Decimal, list[Entry]] = defaultdict(list)
        self._exponents: set[int] = set()
        for entry in entries:
            for sequence in entry.sequences:
                if sequence:
                    self._by_first_token[sequence[0]].append((sequence, entry))
            if entry.amounts is not None:
                for index, values in (
                    (self._exact, entry.amounts.exact),
                    (self._rounded, entry.amounts.rounded),
                    (self._abbreviated, entry.amounts.abbreviated),
                ):
                    for value in values:
                        index[value].append(entry)
                self._exponents.update(map(_exponent, entry.amounts.exact))

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
            for entry in self._amount_matches(line):
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

    def _amount_matches(self, line: str) -> list[Entry]:
        """Return the amount entries written in one line of text.

        A number in the text matches when it equals an entry's value, or a rounded form of it,
        or when the text is more precise than the entry and rounds to the entry's value.
        """
        found: list[Entry] = []
        for amount in amounts_in(line):
            found += self._exact.get(amount, ())
            found += self._rounded.get(amount, ())
            for exponent in self._exponents:
                if _exponent(amount) < exponent:
                    for rounded in _round(amount, exponent):
                        found += self._exact.get(rounded, ())
        for amount in abbreviated_amounts_in(line):
            for index in (self._exact, self._rounded, self._abbreviated):
                found += index.get(amount, ())
        return found


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
