import tomllib
from pathlib import Path

import pytest

import crashmodel
from crashmodel import project

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_installed_version_matches_pyproject() -> None:
    declared = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
    assert crashmodel.__version__ == declared


def test_user_agent_names_the_tool_and_version_only() -> None:
    agent = project.user_agent()
    assert agent.startswith(f"crashmodel/{crashmodel.__version__}")
    assert "@" not in agent


class FakeMetadata:
    def __init__(self, urls: list[str]) -> None:
        self.urls = urls

    def get_all(self, _name: str) -> list[str]:
        return self.urls


def test_repository_url_is_read_from_package_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    urls = ["Homepage, https://example.com", "Repository, https://github.com/example/repo"]
    monkeypatch.setattr(project, "metadata", lambda _package: FakeMetadata(urls))

    assert project.repository_url() == "https://github.com/example/repo"
    assert project.user_agent().endswith("(+https://github.com/example/repo)")


def test_repository_url_is_none_when_not_declared(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(project, "metadata", lambda _package: FakeMetadata([]))
    assert project.repository_url() is None
