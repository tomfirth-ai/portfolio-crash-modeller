"""Privacy scan: stop personal data from reaching the git history.

The scan compares text with a private denylist that lives outside the repository and is written
by hand. The tool itself is generic: nothing in it, or anywhere in the repository, reveals what the
denylist holds.

Matching is forgiving about case, spacing, punctuation, accents and the way amounts and dates are
written: see ``tools.denylist``.

The scan reads the objects git stores, not rendered diffs, so attributes, text conversion drivers
and log settings cannot hide anything, and file names, binary formats and images are judged the
same way at every stage.

Findings say where a match occurred and which denylist line matched, never the matched text, and a
file whose name matches is shown with its name hidden. The scan fails closed: a missing, empty or
in-repository denylist is an error, not a pass.

Usage::

    python -m tools.privacy_scan --staged          # pre-commit: staged content and file names
    python -m tools.privacy_scan --message FILE    # commit-msg: the commit message
    python -m tools.privacy_scan --push            # pre-push: commits the remote does not have
    python -m tools.privacy_scan --all-history     # phase gates: every commit, tag and ref name
"""

import argparse
import os
import sys
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from tools._git import changed_files, decode_text, git, read_objects, repo_root
from tools.denylist import (
    DenylistError,
    Entry,
    Matcher,
    configured_denylist_path,
    load_denylist,
)
from tools.policy import BLOCKED_FORMAT, BLOCKED_SUFFIXES, is_screenshot_path, screenshot_problem

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_CONFIG_ERROR = 2

SHORT_ID_LENGTH = 12
"""Characters of a git object id shown in findings."""
HIDDEN_NAME = "<name hidden>"
"""Shown instead of a file name that matches the denylist."""


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


def scan_text(text: str, matcher: Matcher, location: str) -> list[Finding]:
    """Return one finding per denylist entry found, on the line where each match starts."""
    return [
        Finding(location, f"matches denylist line {entry.line}", line)
        for line, entry in matcher.find(text)
    ]


def scan_documents(documents: Iterable[Document], entries: Sequence[Entry]) -> list[Finding]:
    """Scan file names and contents, refusing binary data formats and unscannable binaries."""
    matcher = Matcher(entries)
    findings: list[Finding] = []
    for document in documents:
        name_matches = [] if document.path is None else matcher.entries_in(document.path)
        location = document.hidden_location() if name_matches else document.location
        findings.extend(
            Finding(location, f"file name matches denylist line {entry.line}")
            for entry in name_matches
        )
        findings.extend(_content_findings(document, location, matcher))
    return findings


def _content_findings(document: Document, location: str, matcher: Matcher) -> list[Finding]:
    path = document.path or ""
    if PurePosixPath(path).suffix.lower() in BLOCKED_SUFFIXES:
        return [Finding(location, BLOCKED_FORMAT)]
    text = decode_text(document.content)
    if text is not None:
        return scan_text(text, matcher, location)
    if is_screenshot_path(path):
        problem = screenshot_problem(document.content)
        if problem is not None:
            return [Finding(location, problem)]
        note = "screenshot pixels cannot be scanned; review it by eye"
        return [Finding(location, note, blocking=False)]
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


def push_revisions(remote: str) -> list[str]:
    """Return the ``git rev-list`` arguments for every commit that ``remote`` does not have yet.

    Every local branch and tag is covered, not only the ref being pushed: pre-commit reports just
    the first ref of a push, and none at all for a repository's first push. Commits that only
    another remote has are scanned too, because publishing to one remote says nothing about
    another.
    """
    return ["HEAD", "--branches", "--tags", "--not", f"--remotes={remote}"]


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stop personal data from reaching the git history."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true", help="scan staged files and their names")
    mode.add_argument("--message", type=Path, metavar="FILE", help="scan a commit message file")
    mode.add_argument(
        "--push", action="store_true", help="scan commits that the remote does not have yet"
    )
    mode.add_argument(
        "--all-history", action="store_true", help="scan every commit, tag and ref name"
    )
    parser.add_argument(
        "--remote",
        default=os.environ.get("PRE_COMMIT_REMOTE_NAME"),
        help="remote being pushed to, with --push (default: $PRE_COMMIT_REMOTE_NAME)",
    )
    parser.add_argument(
        "--denylist", type=Path, help="denylist path (default: git config or ~/.config)"
    )
    args = parser.parse_args(argv)
    if args.push and not args.remote:
        parser.error("--push needs the remote being pushed to: pre-commit sets it, or use --remote")
    return args


def _documents_for(args: argparse.Namespace, repository: Path) -> list[Document]:
    if args.staged:
        return staged_documents(repository)
    if args.message is not None:
        return [Document(args.message.read_bytes(), "commit message")]
    revisions = push_revisions(args.remote) if args.push else ["--all"]
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
