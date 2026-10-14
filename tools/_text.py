"""Reading file content as text."""


def decode_text(content: bytes) -> str | None:
    """Decode file content as UTF-8 text, or return ``None`` if it looks binary."""
    if b"\0" in content:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None
