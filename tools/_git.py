"""Thin helpers for running git from the guard tools."""

import subprocess
from pathlib import Path


def git(*args: str, cwd: Path | None = None) -> bytes:
    """Run a git command and return its standard output.

    Args:
        *args: Arguments passed to git.
        cwd: Directory to run in. Defaults to the current directory.

    Returns:
        The raw standard output.

    Raises:
        subprocess.CalledProcessError: If git exits with a non-zero status.
    """
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=True).stdout


def repo_root(cwd: Path | None = None) -> Path:
    """Return the top-level directory of the enclosing git repository."""
    return Path(git("rev-parse", "--show-toplevel", cwd=cwd).decode().strip())


def tracked_files(cwd: Path | None = None) -> list[str]:
    """Return the paths of every file in the git index, staged additions included."""
    return [path for path in git("ls-files", "-z", cwd=cwd).decode().split("\0") if path]


def decode_text(content: bytes) -> str | None:
    """Decode file content as UTF-8 text, or return ``None`` if it looks binary."""
    if b"\0" in content:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None
