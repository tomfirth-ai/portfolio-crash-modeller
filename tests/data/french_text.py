"""A stand-in for the French library's server, and zipping text as the library serves it.

Every value it serves is a round number made up in ``french_portfolio_text``; no real data from the
library is used or stored.
"""

import io
import zipfile
from dataclasses import dataclass, field

import httpx

from crashmodel.data.french import PORTFOLIO_FILES
from crashmodel.engine.months import Month
from tests.data.french_portfolio_text import portfolio_text


def zipped(text: str, member: str = "Portfolios_Formed_on_ME.csv") -> bytes:
    """Zip CSV text in memory, as the library serves it."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member, text)
    return buffer.getvalue()


LIBRARY_START = Month(1999, 1)
LIBRARY_END = Month(2024, 12)
"""The fake library's files cover every crash window."""


@dataclass
class FakeLibrary:
    """A stand-in for the library's server, serving every size portfolio file as synthetic text.

    Attributes:
        online: Whether it answers; when ``False``, every connection is refused.
        requests: The URL of every request it has received, in order.
    """

    online: bool = True
    requests: list[str] = field(default_factory=list)

    def client(self) -> httpx.Client:
        """Return an HTTP client whose requests go to this fake server."""
        return httpx.Client(transport=httpx.MockTransport(self._answer))

    def _answer(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)
        if not self.online:
            raise httpx.ConnectError("the fake library is offline")
        files = {file.url: file for file in PORTFOLIO_FILES}
        if url not in files:
            return httpx.Response(404)
        months = LIBRARY_END - LIBRARY_START + 1
        text = portfolio_text(files[url], start=LIBRARY_START, months=months)
        return httpx.Response(200, content=zipped(text))
