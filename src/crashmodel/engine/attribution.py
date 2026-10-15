"""Which holdings drove a fall.

From the high to the bottom, a split's value changes by the sum of what each holding gained or lost
in each month in between. So each holding's share of the fall is its own gains over those months,
as a fraction of the value at the high, and the shares add up exactly to the fall: for a 20% fall,
shares of -0.25 and +0.05 mean one holding lost a quarter of the high's value while another made a
twentieth of it back.
"""

from crashmodel.engine.drawdown import Fall
from crashmodel.engine.portfolio import PortfolioPath


def fall_contributions[Key](path: PortfolioPath[Key], fall: Fall) -> dict[Key, float]:
    """Return each holding's gain from the high to the bottom, as a fraction of the high.

    The fractions add up to minus the fall's depth. A negative fraction pulled the split down; a
    positive one held it up.
    """
    high = path.values[fall.peak]
    return {
        key: sum(gains.between(fall.peak + 1, fall.bottom).values) / high
        for key, gains in path.gains.items()
    }
