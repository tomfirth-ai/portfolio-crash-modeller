"""Facts about the project itself, read from the installed package metadata."""

from importlib.metadata import metadata

from crashmodel import __version__

PACKAGE = "crashmodel"


def repository_url() -> str | None:
    """Return the repository URL declared in ``pyproject.toml``, if one is declared."""
    entries: list[str] = metadata(PACKAGE).get_all("Project-URL") or []
    for entry in entries:
        label, _, url = entry.partition(",")
        if label.strip().lower() == "repository":
            return url.strip()
    return None


def user_agent() -> str:
    """Return the User-Agent sent to data publishers: tool name, version and repository.

    Publishers such as the ONS ask automated clients to identify themselves this way, and never
    with a personal name or email address.
    """
    url = repository_url()
    return f"{PACKAGE}/{__version__}" + (f" (+{url})" if url else "")
