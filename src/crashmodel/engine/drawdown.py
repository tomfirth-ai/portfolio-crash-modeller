"""How far a split fell in a crash, how long it fell for, and how long it took to recover.

All figures come from month-end values, so a fall within a month can be deeper than they show.

- The **worst fall** is the biggest drop from a high point to a later low point, where the low
  point comes in the crash phase. Its high point is the latest month at that high, which may be the
  start.
- **Months to bottom** run from that high point to the bottom.
- **Months to recover** run from the bottom to the first month back at the old high, if that happens
  before the window ends. Otherwise the recovery is unknown, not zero.
"""

from dataclasses import dataclass

from crashmodel.engine.months import Month, MonthlySeries

TOLERANCE = 1e-9
"""Relative tolerance for "back at the high": 100 after -40% and +66.67% is 99.99999999999999."""


@dataclass(frozen=True, kw_only=True)
class Fall:
    """The worst fall of a split during a crash.

    Attributes:
        peak: The month of the high point the fall is measured from.
        bottom: The month of the low point.
        depth: How far below the high point the bottom was, as a fraction (0.24 is 24%).
        recovery: The first month back at the high point, or ``None`` if not by the window end.
        still_falling: Whether the bottom came in the last month of the crash phase, so the split
            may not have finished falling.
        deeper_later: If the split fell further after the crash phase and before recovering, how
            far below the high point it then got, as a fraction; otherwise ``None``.
    """

    peak: Month
    bottom: Month
    depth: float
    recovery: Month | None
    still_falling: bool
    deeper_later: float | None

    @property
    def months_to_bottom(self) -> int:
        """Months from the high point to the bottom."""
        return self.bottom - self.peak

    @property
    def months_to_recover(self) -> int | None:
        """Months from the bottom back to the high point, or ``None`` if it was not regained."""
        return None if self.recovery is None else self.recovery - self.bottom


@dataclass(frozen=True, kw_only=True)
class CrashResult:
    """How a split came through a crash.

    Attributes:
        fall: Its worst fall during the crash phase, or ``None`` if it never fell.
        end_value: What 100 at the start was worth at the end of the window.
    """

    fall: Fall | None
    end_value: float


def crash_result(values: MonthlySeries, crash_end: Month) -> CrashResult:
    """Measure a split's path through a crash.

    Args:
        values: The split's value at each month end of the window, from its start to its end.
        crash_end: The last month of the crash phase. Falls that bottom out after it belong to
            another story, such as the 2022 bond sell-off after Covid.

    Raises:
        ValueError: If ``crash_end`` is not after the start and within the window.
    """
    if not values.start < crash_end <= values.end:
        raise ValueError(f"{crash_end} must be after {values.start} and no later than {values.end}")
    return CrashResult(fall=_worst_fall(values, crash_end), end_value=values.values[-1])


def _worst_fall(values: MonthlySeries, crash_end: Month) -> Fall | None:
    points = list(values.items())
    high = points[0][1]
    depth, bottom_index = 0.0, 0
    for index, (month, value) in enumerate(points):
        high = max(high, value)
        drawdown = 1 - value / high
        if month <= crash_end and drawdown > depth + TOLERANCE:
            depth, bottom_index = drawdown, index
    if depth <= TOLERANCE:
        return None
    peak_value = max(value for _, value in points[: bottom_index + 1])
    peak_index = max(
        index
        for index, (_, value) in enumerate(points[: bottom_index + 1])
        if value >= peak_value * (1 - TOLERANCE)
    )
    after_bottom = points[bottom_index + 1 :]
    recovery = next(
        (month for month, value in after_bottom if value >= peak_value * (1 - TOLERANCE)), None
    )
    before_recovery = [
        value
        for month, value in after_bottom
        if month > crash_end and (recovery is None or month < recovery)
    ]
    later_depth = 1 - min(before_recovery) / peak_value if before_recovery else 0.0
    return Fall(
        peak=points[peak_index][0],
        bottom=points[bottom_index][0],
        depth=depth,
        recovery=recovery,
        still_falling=points[bottom_index][0] == crash_end,
        deeper_later=later_depth if later_depth > depth + TOLERANCE else None,
    )
