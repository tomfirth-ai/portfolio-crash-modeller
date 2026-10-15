"""The value of a split over time.

A split is kept at its weights: at every month end it is put back to them, as ready-made multi-asset
funds do. The results then describe the split as designed, not one that has drifted towards
whatever did best. Each month's return is the weighted sum of its holdings' returns:

    r_split = sum of weight_i * r_i

Costs, fees and taxes are not included.
"""

from collections.abc import Mapping

from crashmodel.engine.months import Month, MonthlySeries, month_range

STARTING_VALUE = 100.0
"""Every split starts at 100, so its value reads as what £100 would have become."""
WEIGHT_TOLERANCE = 1e-9


def rebalanced_values[Key](
    weights: Mapping[Key, float], returns: Mapping[Key, MonthlySeries], first: Month, last: Month
) -> MonthlySeries:
    """Return the value of a split kept at its weights, from 100 at the end of ``first``.

    Args:
        weights: Each holding's share of the split as a fraction. They must not be negative and
            must add up to 1. Holdings with no weight need no returns.
        returns: Each holding's monthly returns, covering every month after ``first`` up to
            ``last``.
        first: The month at whose end the split is worth 100.
        last: The final month.

    Raises:
        ValueError: If the weights are invalid, ``last`` is before ``first``, or a holding with
            weight lacks returns for any month.
    """
    if any(weight < 0 for weight in weights.values()):
        raise ValueError("weights cannot be negative")
    if abs(sum(weights.values()) - 1) > WEIGHT_TOLERANCE:
        raise ValueError("weights must add up to 1")
    if last < first:
        raise ValueError(f"{last} is before {first}")
    held = {key: weight for key, weight in weights.items() if weight > 0}
    for key in held:
        if key not in returns or not returns[key].covers(first + 1, last):
            raise ValueError(f"{key} has no returns for some months from {first + 1} to {last}")
    values = [STARTING_VALUE]
    for month in month_range(first + 1, last):
        split_return = sum(weight * returns[key][month] for key, weight in held.items())
        values.append(values[-1] * (1 + split_return))
    return MonthlySeries(first, tuple(values))
