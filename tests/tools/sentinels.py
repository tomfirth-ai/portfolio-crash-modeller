"""Synthetic test data for the guard tools. None of these values is real."""

import zlib
from collections.abc import Callable

from tools.policy import PNG_SIGNATURE

SENTINEL_DENYLIST = """\
# Synthetic sentinels for tests. None of these is real.

Zebedee Quartermaine
ZQXW
271828
314.159
2031-02-17
"""
NAME_LINE, TICKER_LINE, AMOUNT_LINE, UNITS_LINE, DATE_LINE = 3, 4, 5, 6, 7
"""Where each kind of sentinel sits in ``SENTINEL_DENYLIST``."""

GitRunner = Callable[..., str]
"""Runs git in the test repository and returns its standard output."""


def png_chunk(kind: bytes, data: bytes = b"") -> bytes:
    """Build one PNG chunk: length, type, data and checksum."""
    checksum = zlib.crc32(kind + data).to_bytes(4, "big")
    return len(data).to_bytes(4, "big") + kind + data + checksum


def png(*extra_chunks: bytes) -> bytes:
    """Build a one-pixel PNG, with any extra chunks placed before the image data."""
    header = png_chunk(b"IHDR", bytes.fromhex("00000001 00000001 08 00 00 00 00"))
    pixels = png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
    return PNG_SIGNATURE + header + b"".join(extra_chunks) + pixels + png_chunk(b"IEND")
