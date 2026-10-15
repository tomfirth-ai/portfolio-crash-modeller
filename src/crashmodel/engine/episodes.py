"""Crash episodes, and running a split through one.

Each episode is a fixed window taken from events, not from any index level, so every split in it is
measured over the same months and nothing about the window depends on data that may change. It has
three months:

- the **start**, at whose end every split is worth 100, chosen before the crash broke;
- the **end of the crash phase**, after which a fall belongs to another story;
- the **end of the window**, five years after the start, by which recovery is judged.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from crashmodel.engine.drawdown import CrashResult, crash_result
from crashmodel.engine.months import Month, MonthlySeries
from crashmodel.engine.portfolio import rebalanced_values


@dataclass(frozen=True, kw_only=True)
class Episode:
    """A crash, as a fixed window of months.

    Attributes:
        key: A short stable identifier, such as ``"2007-09"``.
        start: The month at whose end every split is worth 100.
        crash_end: The last month of the crash phase.
        end: The last month of the window.
    """

    key: str
    start: Month
    crash_end: Month
    end: Month

    def __post_init__(self) -> None:
        """Reject a window whose months are out of order."""
        if not self.start < self.crash_end <= self.end:
            raise ValueError(f"episode {self.key} needs start < crash end <= end")


GLOBAL_FINANCIAL_CRISIS = Episode(
    key="2007-09", start=Month(2007, 6), crash_end=Month(2009, 6), end=Month(2012, 6)
)
"""Starts before the credit crunch broke in August 2007; the crash phase ends with the UK and US
recessions in mid-2009."""

COVID = Episode(key="2020", start=Month(2019, 12), crash_end=Month(2020, 6), end=Month(2024, 12))
"""Starts as the first cases were reported at the end of 2019; the crash phase ends with the record
fall in output in the second quarter of 2020."""

EPISODES = (GLOBAL_FINANCIAL_CRISIS, COVID)


def missing_holdings[Key](
    episode: Episode, weights: Mapping[Key, float], returns: Mapping[Key, MonthlySeries]
) -> list[Key]:
    """Return the held holdings whose returns do not cover every month of the episode."""
    first, last = episode.start + 1, episode.end
    return [
        key
        for key, weight in weights.items()
        if weight > 0 and (key not in returns or not returns[key].covers(first, last))
    ]


@dataclass(frozen=True, kw_only=True)
class EpisodeRun:
    """A split's path through an episode, and how it came through.

    Attributes:
        values: The split's value at each month end, from 100 at the start.
        result: Its worst fall and recovery, and its value at the end.
    """

    values: MonthlySeries
    result: CrashResult


def run_episode[Key](
    episode: Episode, weights: Mapping[Key, float], returns: Mapping[Key, MonthlySeries]
) -> EpisodeRun:
    """Run a split, kept at its weights, through an episode and measure how it came through.

    Raises:
        ValueError: If a held holding lacks returns for the episode; check ``missing_holdings``
            first to explain why instead.
    """
    values = rebalanced_values(weights, returns, episode.start, episode.end)
    return EpisodeRun(values=values, result=crash_result(values, episode.crash_end))
