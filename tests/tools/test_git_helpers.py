import pytest

from tools._git import decode_text


@pytest.mark.parametrize("content", [b"text\x00with a null byte", b"\xff\xfe not utf-8"])
def test_binary_content_is_not_decoded(content: bytes) -> None:
    assert decode_text(content) is None


def test_utf8_text_is_decoded() -> None:
    assert decode_text("Pound sign: £".encode()) == "Pound sign: £"
