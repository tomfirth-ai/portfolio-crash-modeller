"""Rebuilding share indexes from portfolios of companies grouped by size.

An index such as the S&P 500 or MSCI World holds each company in proportion to its market value,
the price of all its shares. Research data libraries publish the returns of portfolios of companies
grouped by size, with each portfolio's number of firms and their average market value every month.
Their product is the portfolio's market value, so portfolios can be combined just as an index
combines companies:

    r_index[t] = sum of value_i[t] * r_i[t] / sum of value_i[t]

The values describe each portfolio at the start of month t, so they weight that month's returns,
and the weights move as markets rise and fall. An index of the largest N companies takes whole
groups from the largest down until it has N, and counts the last group in proportion to the firms
it needs from it.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from crashmodel.engine.months import Month, MonthlySeries


@dataclass(frozen=True, kw_only=True)
class SizedPortfolio:
    """A portfolio's monthly returns, with how many firms it held and how large they were.

    Attributes:
        returns: Its monthly returns, as decimals.
        firms: How many firms it held at the start of each month.
        average_size: Their average market value at the start of each month, in any unit, as long
            as the portfolios combined use the same one.
    """

    returns: MonthlySeries
    firms: MonthlySeries
    average_size: MonthlySeries

    def __post_init__(self) -> None:
        """Check that the three series cover the same months and that no count or size is negative.

        Raises:
            ValueError: If they do not.
        """
        months = {
            (series.start, series.end) for series in (self.returns, self.firms, self.average_size)
        }
        if len(months) != 1:
            raise ValueError("a portfolio's returns, firms and sizes must cover the same months")
        if min(self.firms.values) < 0 or min(self.average_size.values) < 0:
            raise ValueError("a portfolio cannot hold a negative number of firms or size")


def cap_weighted(portfolios: Sequence[SizedPortfolio]) -> MonthlySeries:
    """Combine portfolios in proportion to their market value at the start of each month.

    Returns:
        The combined monthly returns, for every month all the portfolios cover.

    Raises:
        ValueError: If there are no portfolios, they have no month in common, or a month has no
            market value at all.
    """
    return _combined(portfolios, [portfolio.firms for portfolio in portfolios])


def largest_firms(portfolios: Sequence[SizedPortfolio], count: int) -> MonthlySeries:
    """Return the monthly returns of the ``count`` largest firms, held by market value.

    Args:
        portfolios: Portfolios grouping firms by size, largest first, with no firm in two of them.
        count: How many of the largest firms to hold. When a month has fewer, it holds them all.

    Raises:
        ValueError: If ``count`` is not positive, or as for :func:`cap_weighted`.
    """
    if count <= 0:
        raise ValueError(f"cannot hold the largest {count} firms")
    first, last = _common_months(portfolios)
    held: list[list[float]] = [[] for _ in portfolios]
    for offset in range(last - first + 1):
        month = first + offset
        still_needed = float(count)
        for portfolio, firms in zip(portfolios, held, strict=True):
            taken = min(portfolio.firms[month], still_needed)
            firms.append(taken)
            still_needed -= taken
    return _combined(portfolios, [MonthlySeries(first, tuple(firms)) for firms in held])


def _combined(
    portfolios: Sequence[SizedPortfolio], firms: Sequence[MonthlySeries]
) -> MonthlySeries:
    first, last = _common_months(portfolios)
    combined: list[float] = []
    for offset in range(last - first + 1):
        month = first + offset
        values = [
            held[month] * portfolio.average_size[month]
            for portfolio, held in zip(portfolios, firms, strict=True)
        ]
        total = sum(values)
        if total <= 0:
            raise ValueError(f"no portfolio has any market value in {month}")
        weighted = sum(
            value * portfolio.returns[month]
            for value, portfolio in zip(values, portfolios, strict=True)
        )
        combined.append(weighted / total)
    return MonthlySeries(first, tuple(combined))


def _common_months(portfolios: Sequence[SizedPortfolio]) -> tuple[Month, Month]:
    if not portfolios:
        raise ValueError("there are no portfolios to combine")
    first = max(portfolio.returns.start for portfolio in portfolios)
    last = min(portfolio.returns.end for portfolio in portfolios)
    if first > last:
        raise ValueError("the portfolios have no month in common")
    return first, last
