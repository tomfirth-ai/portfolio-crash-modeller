"""Fund charges: what a fund's yearly ongoing charge takes from each month's return.

A fund pays its ongoing charge out of the money it holds, a little at a time. Taking a twelfth of
the yearly charge each month,

    r_fund = (1 + r_index) * (1 - charge / 12) - 1

so a fund charging 0.12% a year keeps 99.99% of what the index would have given it each month. Over
a year this takes a little less than the charge itself, because each month's twelfth is charged on
what is left after the months before.
"""

from crashmodel.engine.months import MONTHS_IN_YEAR, MonthlySeries


def after_yearly_charge(returns: MonthlySeries, yearly_charge: float) -> MonthlySeries:
    """Return a fund's monthly returns after its yearly ongoing charge.

    Args:
        returns: Monthly returns before charges, such as an index's, as decimals (0.05 is 5%).
        yearly_charge: The charge a year, as a decimal (0.0012 is 0.12%).

    Raises:
        ValueError: If the charge is negative, or would take a whole year's value or more.
    """
    if not 0 <= yearly_charge < 1:
        raise ValueError(f"a yearly charge of {yearly_charge} is not between 0 and 1")
    kept = 1 - yearly_charge / MONTHS_IN_YEAR
    return MonthlySeries(returns.start, tuple((1 + r) * kept - 1 for r in returns.values))
