"""Repository policy shared by the guard tools.

These rules hold whatever ``.gitignore`` says, because ``git add -f`` bypasses ignore rules.
"""

from pathlib import PurePosixPath

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

BLOCKED_FORMAT = "binary data formats are never committed"

IMAGE_SUFFIXES = frozenset({".png"})
"""Screenshots are PNG files, allowed only under ``IMAGE_DIRECTORY`` after a manual review."""

IMAGE_DIRECTORY = "docs/img/"
"""The one directory where reviewed screenshots may live."""

PRIVATE_PREFIXES = ("private/", "local/")
"""Directories that hold private or machine-local files and must never be tracked."""

PRIVATE_FILES = frozenset({"CLAUDE.local.md", ".claude/settings.local.json"})
"""Individual private files that must never be tracked."""

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_METADATA_CHUNKS = frozenset({b"tEXt", b"zTXt", b"iTXt", b"eXIf"})
"""PNG chunks that carry text or EXIF metadata, such as an author's name or a location."""
PNG_END_CHUNK = b"IEND"
PNG_LENGTH_BYTES = 4
PNG_TYPE_BYTES = 4
PNG_CHECKSUM_BYTES = 4


def is_screenshot_path(path: str) -> bool:
    """Whether a path is where a reviewed screenshot may live."""
    return path.startswith(IMAGE_DIRECTORY) and PurePosixPath(path).suffix.lower() in IMAGE_SUFFIXES


def screenshot_problem(content: bytes) -> str | None:
    """Return why a screenshot cannot be committed, or ``None`` if it is a PNG without metadata.

    A by-eye review sees the pixels but not the metadata, and a file renamed to ``.png`` is not an
    image at all, so both are refused. Walks the PNG chunks up to the end chunk.
    """
    if not content.startswith(PNG_SIGNATURE):
        return "not a PNG file, whatever its name says"
    position = len(PNG_SIGNATURE)
    header_bytes = PNG_LENGTH_BYTES + PNG_TYPE_BYTES
    while position + header_bytes <= len(content):
        length = int.from_bytes(content[position : position + PNG_LENGTH_BYTES], "big")
        kind = content[position + PNG_LENGTH_BYTES : position + header_bytes]
        if kind in PNG_METADATA_CHUNKS:
            return "PNG carries text or EXIF metadata; export it again without metadata"
        if kind == PNG_END_CHUNK:
            return None
        position += header_bytes + length + PNG_CHECKSUM_BYTES
    return "PNG is incomplete"
