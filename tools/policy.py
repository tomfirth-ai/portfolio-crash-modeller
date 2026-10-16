"""Repository policy shared by the guard tools.

These rules hold whatever ``.gitignore`` says, because ``git add -f`` bypasses ignore rules.
"""

from pathlib import PurePosixPath

BLOCKED_SUFFIXES = frozenset(
    {
        ".db",
        ".feather",
        ".ipynb",
        ".numbers",
        ".ods",
        ".parquet",
        ".pdf",
        ".pkl",
        ".sqlite",
        ".sqlite3",
        ".xls",
        ".xlsb",
        ".xlsm",
        ".xlsx",
        ".zip",
    }
)
"""Data and document formats that are never committed, because no text scan can see inside them.

Journal files such as ``store.db-wal`` count as their database's format.
"""

BLOCKED_FORMAT = "binary data formats are never committed"

IMAGE_SUFFIXES = frozenset({".png"})
"""Screenshots are PNG files, allowed only under ``IMAGE_DIRECTORY`` after a manual review."""

IMAGE_DIRECTORY = "docs/img/"
"""The one directory where reviewed screenshots may live."""

REFERENCE_DATA_DIRECTORY = "src/crashmodel/data/reference/"
"""Where the committed open data lives: monthly series generated from public publishers' files."""

FUND_CATALOGUE = "src/crashmodel/data/funds.csv"
"""The funds a split can hold: public names, tickers, charges and dates, typed in by hand."""
FUND_COLUMNS = ("index", "provider", "name", "ticker", "yearly_charge", "launched", "documented")
FUND_INDEXES = (
    "S&P 500",
    "MSCI World",
    "FTSE Developed",
    "FTSE All-World",
    "MSCI ACWI",
    "FTSE Global All Cap",
    "MSCI ACWI IMI",
    "FTSE Actuaries UK Conventional Gilts All Stocks",
    "Bloomberg UK Gilt",
    "Bloomberg Sterling Gilt Float Adjusted",
    "FTSE Actuaries UK Conventional Gilts Up to 5 Years",
    "Bloomberg UK Gilt 1-5 Year",
    "Bloomberg UK Gilt 1-5 Year Float Adjusted",
    "J.P. Morgan GBI United Kingdom Short-term Custom Maturity",
    "FTSE Actuaries UK Conventional Gilts Over 15 Years",
    "Bloomberg UK Gilt 15+ Year",
    "Bloomberg U.K. Government 15+ Years Float Adjusted",
    "SONIA",
)
FUND_PROVIDERS = (
    "Amundi",
    "Fidelity",
    "HSBC",
    "Invesco",
    "iShares",
    "L&G",
    "SPDR",
    "UBS",
    "Vanguard",
    "Xtrackers",
)
"""The only index and manager names a line of the fund list may give."""
FUND_TICKER = r"[A-Z0-9]{3,5}"
FUND_CHARGE = r"[0-9]\.[0-9]{2,3}"
"""A London ticker, and an ongoing charge in percent as a key information document prints it.

The catalogue that reads the fund list has its own copy of these formats, and of the columns, the
indexes and the managers; a test keeps the two in step.
"""

PRIVATE_DIRECTORIES = frozenset({"private", "local"})
"""Directories, at any depth, that hold private or machine-local files."""

PRIVATE_FILE_NAMES = frozenset(
    {"CLAUDE.local.md", "settings.local.json", "secrets.toml", ".env", "denylist.txt"}
)
"""Files, in any directory, that hold private notes, local settings, secrets or the denylist."""

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_METADATA_CHUNKS = frozenset({b"tEXt", b"zTXt", b"iTXt", b"eXIf"})
"""PNG chunks that carry text or EXIF metadata, such as an author's name or a location."""
PNG_END_CHUNK = b"IEND"
PNG_LENGTH_BYTES = 4
PNG_TYPE_BYTES = 4
PNG_CHECKSUM_BYTES = 4


def is_private_path(path: str) -> bool:
    """Whether a path is a private file or lies in a private directory."""
    *directories, name = PurePosixPath(path).parts
    return name in PRIVATE_FILE_NAMES or not PRIVATE_DIRECTORIES.isdisjoint(directories)


def is_blocked_format(path: str) -> bool:
    """Whether a path has a blocked suffix, counting ``.db-wal`` and the like as ``.db``."""
    suffix = PurePosixPath(path).suffix.lower()
    return suffix.split("-")[0] in BLOCKED_SUFFIXES


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
