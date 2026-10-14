"""Helpers shared by the guard tool tests."""

import zlib
from typing import Protocol

from tools.policy import PNG_SIGNATURE


class GitRunner(Protocol):
    """Runs git in the test repository and returns its standard output."""

    def __call__(self, *args: str, env: dict[str, str] | None = None) -> str:
        """Run git with these arguments and extra environment variables."""
        ...


def png_chunk(kind: bytes, data: bytes = b"") -> bytes:
    """Build one PNG chunk: length, type, data and checksum."""
    checksum = zlib.crc32(kind + data).to_bytes(4, "big")
    return len(data).to_bytes(4, "big") + kind + data + checksum


def png(*extra_chunks: bytes) -> bytes:
    """Build a one-pixel PNG, with any extra chunks placed before the image data."""
    header = png_chunk(b"IHDR", bytes.fromhex("00000001 00000001 08 00 00 00 00"))
    pixels = png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
    return PNG_SIGNATURE + header + b"".join(extra_chunks) + pixels + png_chunk(b"IEND")
