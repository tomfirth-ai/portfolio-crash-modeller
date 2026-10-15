"""The value of a split over time, and what each holding gained or lost along the way.

A split can be managed in two ways:

- **Kept at its weights**: at every month end it is put back to them, much as ready-made
  multi-asset funds keep a fixed mix. Each month's return is then the weighted sum of its holdings'
  returns, ``r_split = sum of weight_i * r_i``, and the results describe the split as designed.
- **Left alone**: bought once and never touched, so whatever does well grows to a larger share.

Either way, each month a holding gains its return on the amount in it at the start of the month,
and the split's value is the sum of its holdings. Recording those gains is what lets a fall be
explained holding by holding. Costs, fees and taxes are not included.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from crashmodel.engine.months import Month, MonthlySeries

STARTING_VALUE = 100.0
"""Every split starts at 100, so its value reads as what £100 would have become."""
WEIGHT_TOLERANCE = 1e-9


class Rebalancing(Enum):
    """How a split is managed between month ends."""

    MONTHLY = "monthly"
    """Put back to its weights at every month end."""
    NEVER = "never"
    """Bought once and left alone."""


@dataclass(frozen=True, kw_only=True)
class PortfolioPath[Key]:
    """A split's value at each month end, and what each holding gained in each month.

    Attributes:
        values: The split's value at each month end, from 100 at the end of the first month.
        gains: For each holding with a weight, its gain in each later month, in the same units
            as ``values``; a loss is negative. Each month's gains add up to the change in value.
    """

    values: MonthlySeries
    gains: Mapping[Key, MonthlySeries]


def portfolio_path[Key](
    weights: Mapping[Key, float],
    returns: Mapping[Key, MonthlySeries],
    first: Month,
    last: Month,
    rebalancing: Rebalancing = Rebalancing.MONTHLY,
) -> PortfolioPath[Key]:
    """Return the path of a split worth 100 at the end of ``first``, managed as given.

    Args:
        weights: Each holding's share of the split as a fraction. They must not be negative and
            must add up to 1. Holdings with no weight need no returns.
        returns: Each holding's monthly returns, covering every month after ``first`` up to
            ``last``.
        first: The month at whose end the split is worth 100.
        last: The final month, after ``first``.
        rebalancing: Whether the split is put back to its weights every month or left alone.

    Raises:
        ValueError: If the weights are invalid, ``last`` is not after ``first``, or a holding with
            weight lacks returns for any month.
    """
    if any(weight < 0 for weight in weights.values()):
        raise ValueError("weights cannot be negative")
    if abs(sum(weights.values()) - 1) > WEIGHT_TOLERANCE:
        raise ValueError("weights must add up to 1")
    if last <= first:
        raise ValueError(f"{last} is not after {first}")
    held = {key: weight for key, weight in weights.items() if weight > 0}
    for key in held:
        if key not in returns or not returns[key].covers(first + 1, last):
            raise ValueError(f"{key} has no returns for some months from {first + 1} to {last}")
    monthly = {key: returns[key].between(first + 1, last).values for key in held}
    amounts = {key: STARTING_VALUE * weight for key, weight in held.items()}
    values = [STARTING_VALUE]
    gains: dict[Key, list[float]] = {key: [] for key in held}
    for offset in range(last - first):
        if rebalancing is Rebalancing.MONTHLY:
            amounts = {key: values[-1] * weight for key, weight in held.items()}
        gained = {key: amount * monthly[key][offset] for key, amount in amounts.items()}
        for key, gain in gained.items():
            gains[key].append(gain)
        amounts = {key: amount + gained[key] for key, amount in amounts.items()}
        values.append(sum(amounts.values()))
    return PortfolioPath(
        values=MonthlySeries(first, tuple(values)),
        gains={key: MonthlySeries(first + 1, tuple(series)) for key, series in gains.items()},
    )
