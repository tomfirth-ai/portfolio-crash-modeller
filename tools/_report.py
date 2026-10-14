"""How the guard tools describe problems and exit."""

import sys
from collections.abc import Sequence
from dataclasses import dataclass

EXIT_CLEAN = 0
EXIT_PROBLEMS = 1
EXIT_CONFIG_ERROR = 2
"""The tool is not set up correctly, so it could not check anything. Argparse exits with 2 too."""


@dataclass(frozen=True)
class Problem:
    """A problem found by a guard tool.

    Attributes:
        location: Where it was found, usually a path.
        message: What was found.
        line: Line number within the location, when there is one.
    """

    location: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        """Format the problem as ``location:line: message``, which editors can follow."""
        where = self.location if self.line is None else f"{self.location}:{self.line}"
        return f"{where}: {self.message}"


def report(tool: str, problems: Sequence[Problem]) -> int:
    """Print each problem to standard error and return the matching exit code."""
    for problem in problems:
        print(f"{tool}: {problem}", file=sys.stderr)
    return EXIT_PROBLEMS if problems else EXIT_CLEAN
