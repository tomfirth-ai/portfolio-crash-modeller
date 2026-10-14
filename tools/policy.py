"""Repository policy shared by the guard tools.

These rules hold whatever ``.gitignore`` says, because ``git add -f`` bypasses ignore rules.
"""

BLOCKED_SUFFIXES = frozenset(
    {
        ".db",
        ".feather",
        ".ipynb",
        ".ods",
        ".parquet",
        ".pkl",
        ".sqlite",
        ".sqlite3",
        ".xls",
        ".xlsx",
        ".zip",
    }
)
"""Binary data formats that are never committed, because no text scan can see inside them."""

IMAGE_SUFFIXES = frozenset({".gif", ".jpeg", ".jpg", ".png", ".webp"})
"""Image formats, allowed only under ``IMAGE_DIRECTORY`` after a manual review."""

IMAGE_DIRECTORY = "docs/img/"
"""The one directory where reviewed screenshots may live."""

PRIVATE_PREFIXES = ("private/", "local/")
"""Directories that hold private or machine-local files and must never be tracked."""

PRIVATE_FILES = frozenset({"CLAUDE.local.md", ".claude/settings.local.json"})
"""Individual private files that must never be tracked."""
