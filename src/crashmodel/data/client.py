"""The HTTP client every download uses.

It names the project in its User-Agent, as polite automated clients do, follows redirects, and gives
up quickly on a server that does not answer, so a page never hangs on a slow source.
"""

import httpx

from crashmodel.project import user_agent

CONNECT_TIMEOUT_SECONDS = 4.0
READ_TIMEOUT_SECONDS = 10.0


def make_client() -> httpx.Client:
    """Return an HTTP client that identifies the project, follows redirects and times out."""
    return httpx.Client(
        timeout=httpx.Timeout(READ_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS),
        follow_redirects=True,
        headers={"User-Agent": user_agent()},
    )
