"""Crash episodes, and running a split through one.

Each episode is a fixed window taken from events, not from any index level, so every split in it is
measured over the same months and nothing about the window depends on data that may change. It has
three months:

- the **start**, at whose end every split is worth 100, chosen before the crash broke;
- the **end of the crash phase**, after which a fall belongs to another story;
- the **end of the window**, by which recovery is judged.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from crashmodel.engine.drawdown import CrashResult, crash_result
from crashmodel.engine.months import Month, MonthlySeries
from crashmodel.engine.portfolio import PortfolioPath, Rebalancing, portfolio_path


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


DOT_COM = Episode(key="2000-03", start=Month(2000, 2), crash_end=Month(2003, 3), end=Month(2005, 2))
"""Starts before the technology bubble burst in March 2000; the crash phase ends as the Iraq war
began in March 2003, after the US recession of 2001, the September 2001 attacks and the accounting
scandals of 2002."""

GLOBAL_FINANCIAL_CRISIS = Episode(
    key="2007-09", start=Month(2007, 6), crash_end=Month(2009, 6), end=Month(2012, 6)
)
"""Starts before the credit crunch broke in August 2007; the crash phase ends with the UK and US
recessions in mid-2009."""

COVID = Episode(key="2020", start=Month(2019, 12), crash_end=Month(2020, 6), end=Month(2024, 12))
"""Starts as the first cases were reported at the end of 2019; the crash phase ends with the record
fall in output in the second quarter of 2020."""

BOND_CRASH = Episode(
    key="2022-23", start=Month(2021, 12), crash_end=Month(2023, 10), end=Month(2024, 12)
)
"""Starts as the Bank of England began raising Bank Rate in December 2021; the crash phase ends in
October 2023, after the last rise, in August 2023, with gilt yields at their highest."""

EPISODES = (DOT_COM, GLOBAL_FINANCIAL_CRISIS, COVID, BOND_CRASH)
"""Every crash, oldest first."""
EPISODES_BY_KEY = {episode.key: episode for episode in EPISODES}


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
class EpisodeRun[Key]:
    """A split's path through an episode, and how it came through.

    Attributes:
        path: The split's value at each month end, from 100 at the start, and each holding's
            gain in each month.
        result: Its worst fall and recovery, and its value at the end.
    """

    path: PortfolioPath[Key]
    result: CrashResult

    @property
    def values(self) -> MonthlySeries:
        """The split's value at each month end, from 100 at the start."""
        return self.path.values


def run_episode[Key](
    episode: Episode,
    weights: Mapping[Key, float],
    returns: Mapping[Key, MonthlySeries],
    rebalancing: Rebalancing = Rebalancing.MONTHLY,
) -> EpisodeRun[Key]:
    """Run a split through an episode, managed as given, and measure how it came through.

    Raises:
        ValueError: If a held holding lacks returns for the episode; check ``missing_holdings``
            first to explain why instead.
    """
    path = portfolio_path(weights, returns, episode.start, episode.end, rebalancing)
    return EpisodeRun(path=path, result=crash_result(path.values, episode.crash_end))
