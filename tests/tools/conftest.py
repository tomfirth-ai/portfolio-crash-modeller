import os
import subprocess
from pathlib import Path

import pytest

from tests.tools.sentinels import SENTINEL_DENYLIST, GitRunner


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty git repository, isolated from the user's own git configuration, as the cwd."""
    home = tmp_path / "home"
    home.mkdir()
    empty_config = home / ".gitconfig"
    empty_config.touch()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test Author")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.com")
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    monkeypatch.chdir(root)
    return root


@pytest.fixture
def run_git(repo: Path) -> GitRunner:
    """Run git in the test repository and return its standard output."""

    def run(*args: str, env: dict[str, str] | None = None) -> str:
        merged = {**os.environ, **(env or {})}
        result = subprocess.run(
            ["git", *args], cwd=repo, env=merged, capture_output=True, check=True, text=True
        )
        return result.stdout

    return run


@pytest.fixture
def denylist(tmp_path: Path) -> Path:
    """A denylist of synthetic sentinels, stored outside the repository."""
    path = tmp_path / "outside" / "denylist.txt"
    path.parent.mkdir()
    path.write_text(SENTINEL_DENYLIST, encoding="utf-8")
    return path
