"""Privacy scan: stop personal data from reaching the git history.

The scan compares text with a private denylist that lives outside the repository and is written
by hand. The tool itself is generic: nothing in it, or anywhere in the repository, reveals what the
denylist holds.

Matching is forgiving, so that small changes of form do not slip through:

* words are compared as sequences of tokens after splitting on spaces, punctuation,
  ``snake_case`` and ``camelCase`` and ignoring case, so ``Jane Doe``, ``jane_doe`` and
  ``janeDoe`` all match ``Jane Doe``, while a short entry never matches inside a longer word;
* amounts are compared by value, so ``271828`` also matches ``271,828``, ``271828.00``, the same
  amount in pence and the same amount divided by 100;
* ISO dates such as ``2031-02-17`` also match the common UK, US and long-form spellings.

The scan reads the objects git stores, not rendered diffs, so attributes, text conversion drivers
and log settings cannot hide anything, and file names, binary formats and images are judged the
same way at every stage.

Findings say where a match occurred and which denylist line matched, never the matched text, and a
file whose name matches is shown with its name hidden. The scan fails closed: a missing, empty or
in-repository denylist is an error, not a pass.

Usage::

    python -m tools.privacy_scan --staged          # pre-commit: staged content and file names
    python -m tools.privacy_scan --message FILE    # commit-msg: the commit message
    python -m tools.privacy_scan --push            # pre-push: commits that no remote has yet
    python -m tools.privacy_scan --all-history     # phase gates: every commit, tag and ref name
"""

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path, PurePosixPath

from tools._git import changed_files, decode_text, git, read_objects, repo_root
from tools.policy import BLOCKED_SUFFIXES, IMAGE_DIRECTORY, IMAGE_SUFFIXES

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_CONFIG_ERROR = 2

GIT_CONFIG_KEY = "crashmodel.denylist"
MIN_DISTINCTIVE_DIGITS = 4
"""Rounded or rescaled amounts with fewer digits than this are too common to match safely."""
MIN_DISTINCTIVE_CHARACTERS = 3
"""Word entries shorter than this are matched, but trigger a false-positive warning."""
SHORT_ID_LENGTH = 12
"""Characters of a git object id shown in findings."""
HIDDEN_NAME = "<name hidden>"
"""Shown instead of a file name that matches the denylist."""
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
    """

    line: int
    sequences: tuple[tuple[str, ...], ...]
    amounts: frozenset[Decimal] = field(default_factory=frozenset)

    def matches(self, tokens: Sequence[str], amounts: frozenset[Decimal]) -> bool:
        """Return whether a line with these tokens and amounts contains this entry."""
        if not self.amounts.isdisjoint(amounts):
            return True
        return any(contains_sequence(tokens, sequence) for sequence in self.sequences)

    @property
    def is_short(self) -> bool:
        """Whether the entry is so short that it may cause false positives."""
        longest = max((len("".join(sequence)) for sequence in self.sequences), default=0)
        return longest < MIN_DISTINCTIVE_CHARACTERS


@dataclass(frozen=True)
class Finding:
    """Something the scan found, described without the matched text.

    Attributes:
        location: Where it was found.
        reason: What was found.
        line: Line number within the location, when there is one.
        blocking: Whether it stops the commit or push. Non-blocking findings are notes.
    """

    location: str
    reason: str
    line: int | None = None
    blocking: bool = True

    def __str__(self) -> str:
        """Format the finding as ``location:line: reason``."""
        where = self.location if self.line is None else f"{self.location}:{self.line}"
        return f"{where}: {self.reason}"


@dataclass(frozen=True)
class Document:
    """Content to scan, and where it comes from.

    Attributes:
        content: The bytes to scan.
        location: Where the content comes from, as shown in findings.
        path: The file's path in the repository, checked against the denylist like its content.
            ``None`` for commit details, messages and ref names, which have no file name.
    """

    content: bytes
    location: str
    path: str | None = None

    def hidden_location(self) -> str:
        """Return the location with the file name replaced, for when the name itself matches."""
        return self.location if self.path is None else self.location.replace(self.path, HIDDEN_NAME)


def tokenise(text: str) -> tuple[str, ...]:
    """Split text into lower-case word and number tokens.

    Splits on anything that is not a letter or digit, between letters and digits, and at
    ``camelCase`` boundaries, after Unicode normalisation (NFKC) so lookalike characters compare
    equal.
    """
    tokens: list[str] = []
    for run in _WORD_OR_NUMBER_RUN.findall(unicodedata.normalize("NFKC", text)):
        tokens.extend(part.casefold() for part in _CASE_BOUNDARY.split(run) if part)
    return tuple(tokens)


def contains_sequence(haystack: Sequence[str], needle: Sequence[str]) -> bool:
    """Return whether ``needle`` occurs as a contiguous run inside ``haystack``."""
    width = len(needle)
    if width == 0:
        return False
    target = tuple(needle)
    return any(
        tuple(haystack[start : start + width]) == target
        for start in range(len(haystack) - width + 1)
    )


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


def parse_entry(line: int, raw: str) -> Entry:
    """Prepare one denylist line for matching, treating amounts and ISO dates specially."""
    text = raw.strip()
    if (amount := parse_amount(text)) is not None:
        plain = format(amount.normalize(), "f")
        return Entry(line, sequences=(tokenise(plain),), amounts=amount_variants(amount))
    if (iso := _ISO_DATE.fullmatch(text)) is not None:
        day = date(*(int(part) for part in iso.groups()))
        return Entry(line, sequences=tuple(tokenise(spelling) for spelling in date_spellings(day)))
    return Entry(line, sequences=(tokenise(text),))


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


def amounts_in(text: str) -> frozenset[Decimal]:
    """Return every number written in the text, normalised for comparison by value."""
    return frozenset(
        Decimal(match.replace(",", "")).normalize() for match in _AMOUNT_IN_TEXT.findall(text)
    )


def matching_entries(line: str, entries: Sequence[Entry]) -> list[Entry]:
    """Return the entries that occur in a single line of text."""
    tokens, amounts = tokenise(line), amounts_in(line)
    return [entry for entry in entries if entry.matches(tokens, amounts)]


def scan_text(text: str, entries: Sequence[Entry], location: str) -> list[Finding]:
    """Scan text line by line and return one finding per matching entry per line."""
    return [
        Finding(location, f"matches denylist line {entry.line}", number)
        for number, line in enumerate(text.splitlines(), start=1)
        for entry in matching_entries(line, entries)
    ]


def scan_documents(documents: Iterable[Document], entries: Sequence[Entry]) -> list[Finding]:
    """Scan file names and contents, refusing binary data formats and unscannable binaries."""
    findings: list[Finding] = []
    for document in documents:
        name_matches = [] if document.path is None else matching_entries(document.path, entries)
        location = document.hidden_location() if name_matches else document.location
        findings.extend(
            Finding(location, f"file name matches denylist line {entry.line}")
            for entry in name_matches
        )
        findings.extend(_content_findings(document, location, entries))
    return findings


def _content_findings(document: Document, location: str, entries: Sequence[Entry]) -> list[Finding]:
    suffix = PurePosixPath(document.path or "").suffix.lower()
    if suffix in BLOCKED_SUFFIXES:
        return [Finding(location, "binary data formats are never committed")]
    text = decode_text(document.content)
    if text is not None:
        return scan_text(text, entries, location)
    if suffix in IMAGE_SUFFIXES and (document.path or "").startswith(IMAGE_DIRECTORY):
        return [Finding(location, "image not scanned; review it by eye", blocking=False)]
    return [Finding(location, "binary file cannot be scanned")]


def staged_documents(repository: Path) -> list[Document]:
    """Return every staged file that is not a deletion, as it stands in the git index.

    Type changes, such as a symbolic link replaced by a file, are included like any other change.
    """
    files = changed_files(
        git(
            *("diff", "--cached", "--raw", "-z", "--no-color", "--no-abbrev", "--no-renames"),
            "--diff-filter=d",
            cwd=repository,
        )
    )
    contents = read_objects(
        (file.object_id for file in files if not file.is_submodule), cwd=repository
    )
    return [Document(contents.get(file.object_id, b""), file.path, file.path) for file in files]


def history_documents(repository: Path, revisions: Sequence[str]) -> list[Document]:
    """Return the commits in ``revisions`` as documents: their details, then each changed file.

    A file that appears unchanged in several commits is scanned once, but a file name is always
    checked, so content committed once under a clean name and again under a matching name is
    still caught.
    """
    commits = git("rev-list", *revisions, cwd=repository).decode().split()
    files_by_commit = {
        commit: changed_files(
            git(
                *("diff-tree", "-r", "-z", "-m", "--root", "--no-commit-id", "--no-abbrev"),
                *("--no-renames", "--diff-filter=d", commit),
                cwd=repository,
            )
        )
        for commit in commits
    }
    blob_ids = (
        file.object_id
        for files in files_by_commit.values()
        for file in files
        if not file.is_submodule
    )
    objects = read_objects([*commits, *blob_ids], cwd=repository)
    documents: list[Document] = []
    seen: set[tuple[str, str]] = set()
    for commit, files in files_by_commit.items():
        short_id = commit[:SHORT_ID_LENGTH]
        details = object_details(objects[commit], headers=(b"author", b"committer"))
        documents.append(Document(details, f"commit {short_id}"))
        for file in files:
            if (file.path, file.object_id) not in seen:
                seen.add((file.path, file.object_id))
                content = objects.get(file.object_id, b"")
                documents.append(Document(content, f"{short_id}:{file.path}", file.path))
    return documents


def tag_documents(repository: Path) -> list[Document]:
    """Return the tagger and message of every annotated tag."""
    references = git(
        "for-each-ref", "--format=%(objectname) %(objecttype)", "refs/tags", cwd=repository
    )
    tag_ids = [
        object_id
        for object_id, kind in (line.split() for line in references.decode().splitlines())
        if kind == "tag"
    ]
    objects = read_objects(tag_ids, cwd=repository)
    return [
        Document(
            object_details(objects[tag_id], headers=(b"tagger",)),
            f"tag object {tag_id[:SHORT_ID_LENGTH]}",
        )
        for tag_id in tag_ids
    ]


def reference_names_document(repository: Path) -> Document:
    """Return the names of every branch and tag, which are published when they are pushed."""
    names = git(
        "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/tags", cwd=repository
    )
    return Document(names, "branch and tag names")


def object_details(raw: bytes, headers: Collection[bytes]) -> bytes:
    """Keep the chosen header lines and the message of a raw commit or tag object.

    The other headers hold object ids and signatures, whose random letters and digits would only
    cause false matches.
    """
    head, _, message = raw.partition(b"\n\n")
    kept = [line for line in head.split(b"\n") if line.partition(b" ")[0] in headers]
    return b"\n".join([*kept, b"", message])


def configured_denylist_path(repository: Path) -> Path:
    """Return the denylist path from ``git config crashmodel.denylist``, or the default location."""
    try:
        configured = git("config", "--get", GIT_CONFIG_KEY, cwd=repository).decode().strip()
    except subprocess.CalledProcessError:
        configured = ""
    return (
        Path(configured) if configured else Path.home() / ".config" / "crashmodel" / "denylist.txt"
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stop personal data from reaching the git history."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true", help="scan staged files and their names")
    mode.add_argument("--message", type=Path, metavar="FILE", help="scan a commit message file")
    mode.add_argument("--push", action="store_true", help="scan commits that no remote has yet")
    mode.add_argument(
        "--all-history", action="store_true", help="scan every commit, tag and ref name"
    )
    parser.add_argument(
        "--denylist", type=Path, help="denylist path (default: git config or ~/.config)"
    )
    return parser.parse_args(argv)


def _documents_for(args: argparse.Namespace, repository: Path) -> list[Document]:
    if args.staged:
        return staged_documents(repository)
    if args.message is not None:
        return [Document(args.message.read_bytes(), "commit message")]
    if args.push:
        target = os.environ.get("PRE_COMMIT_TO_REF") or "HEAD"
        revisions = [target, "--not", "--remotes"]
    else:
        revisions = ["--all"]
    return [
        *history_documents(repository, revisions),
        *tag_documents(repository),
        reference_names_document(repository),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the scan and return a process exit code (0 clean, 1 findings, 2 configuration error)."""
    args = _parse_args(argv)
    repository = repo_root()
    try:
        entries = load_denylist(args.denylist or configured_denylist_path(repository), repository)
    except DenylistError as error:
        print(
            f"privacy scan: {error}. Nothing can be committed until this is fixed.", file=sys.stderr
        )
        return EXIT_CONFIG_ERROR
    for entry in entries:
        if entry.is_short:
            print(
                f"privacy scan: denylist line {entry.line} is short; expect false positives",
                file=sys.stderr,
            )
    findings = scan_documents(_documents_for(args, repository), entries)
    for finding in findings:
        prefix = "privacy scan:" if finding.blocking else "privacy scan: note:"
        print(f"{prefix} {finding}", file=sys.stderr)
    problems = sum(finding.blocking for finding in findings)
    if problems:
        print(
            f"privacy scan: {problems} problem(s) found; nothing was committed or pushed",
            file=sys.stderr,
        )
        return EXIT_FINDINGS
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
