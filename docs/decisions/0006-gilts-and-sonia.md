# 6. Gilt funds and sterling cash from the Bank of England's curves

Date: 16 October 2026. Status: accepted. Amends [ADR 0003](0003-stress-test-method.md), whose
10-year gilt and Bank Rate cash it replaces, [ADR 0004](0004-vertical-slices.md), whose gilt
returns from the 10-year par yield it replaces, and [ADR 0005](0005-real-funds-modelled.md), whose
UK gilt and sterling money market models it replaces.

## Context

Every gilt holding was one 10-year gilt bought new each month. That cannot tell a short gilt fund
from a long one, and in a crash driven by rising interest rates the two behave very differently:
the longer a gilt has to run, the more its price falls when yields rise. Sterling cash earned Bank
Rate, while the money market funds the app lists track SONIA, the overnight rate the Bank of
England administers.

The Bank publishes its estimated gilt yield curves and SONIA in its database, under the Open
Government Licence, so models of whole gilt indexes can be built from data the project may store.

## Decision

- **Data stored with the app**, from the Bank of England database, under the Open Government
  Licence v3.0, written by `tools/build_reference_data.py` with a source note beside each folder:
  - `boe-yield-curve/`: the month-end 5, 10 and 20-year nominal zero-coupon yields (`IUMSNZC` and
    `IUMMNZC` from January 1982, `IUMLNZC` from March 1992), which are continuously compounded, and
    the month-end 5-year nominal par yield (`IUMSNPY`, from December 1993).
  - `boe-sterling-cash/`: the monthly return on cash earning SONIA (`IUDSOIA`, from January 1997),
    and Bank Rate (`IUDBEDR`) before it; and Bank Rate at each month end. SONIA is credited with
    the Bank's own statement: "SONIA and/or SONIA Compounded Index data licensed under the Open
    Government Licence v3.0 and copyright the Governor and Company of the Bank of England. The
    trade marks "Bank of England" and "SONIA" are registered trade marks of the Bank of England."
    The monthly returns are worked out by the app, not by the Bank.
- **Cash** earns each calendar day's rate, `rate / 100 / 365`, compounded daily, with the last
  published rate carried over weekends and holidays, much as SONIA's compounded index grows (that
  index compounds each business day, with simple interest over weekends and holidays). It replaces
  the simple daily sum of ADR 0003, for Bank Rate as well as SONIA.
- **The zero curve of each month** has four points: Bank Rate at the month end, converted to the
  continuously compounded rate that earns as much, `365 * ln(1 + rate / 100 / 365)`, and the 5, 10
  and 20-year zero yields. Bank Rate rather than SONIA stands at term zero because SONIA's month
  ends jump about, more so before 2006. Yields between points lie on a straight line; beyond the
  longest point the curve stays at its yield. A cash flow `t` years away is worth
  `exp(-z(t) / 100 * t)` today. Read this way, the curve's 5-year par coupon stays within 0.15
  points of the Bank's own 5-year par yield in every month, which a test checks; read as compounded
  half-yearly it would not.
- **Gilts as a ladder.** A gilt index holds gilts with every length of time left to run, many of
  them issued years ago with coupons set by the yields of their day. The model holds, at every half
  year of time left to run, gilts first issued at 5, 10, 30 and 50 years (each whose original term
  is at least the time left), in equal amounts. Each pays twice a year the coupon that made it
  worth its face value in the month it was issued, priced off that month's curve. Curves run from
  January 1982, when the 5 and 10-year yields begin, and until the 20-year yield begins in March
  1992 they stay at the 10-year yield beyond 10 years; a gilt issued before January 1982 takes that
  month's coupon. Each month every gilt is valued just after a coupon and again a month later off
  the new curve, and the ladder's return is the change in the value of the whole ladder. Rungs are
  counted at face value, as an index counts the amount of each gilt in issue, and the same amounts
  are held each month.
- **Three gilt models**, each standing for every index in its maturity band:
  - *All maturities* (FTSE Actuaries UK Conventional Gilts All Stocks; Bloomberg UK Gilt, with or
    without float adjustment): the ladder from half a year to 50 years, with 30% of its gilts at
    face value up to 5 years, 35% from 5 to 15 years and 35% over 15 years, spread evenly within
    each band.
  - *Over 15 years* (FTSE Actuaries UK Conventional Gilts Over 15 Years; Bloomberg UK Gilt 15+ Year,
    with or without float adjustment): the ladder from 15.5 to 50 years, spread evenly.
  - *Up to 5 years* (FTSE Actuaries UK Conventional Gilts Up to 5 Years; the Bloomberg and
    J.P. Morgan short-dated gilt indexes, up to 5 or from 1 to 5 years): half a 5-year gilt bought
    new each month at the 5-year par yield, by Swinkels' formula of ADR 0003, and half cash earning
    SONIA, put back to half and half each month.

  The weights and terms describe the indexes' usual shape; none was fitted to an index's returns.
- **The 2022-23 bond crash** joins the crash windows:

  | Crash | Worth 100 at the end of | Crash phase ends | Window ends |
  |---|---|---|---|
  | 2022-23 bond crash | December 2021 | October 2023 | December 2024 |

  The start comes as the Bank of England began raising Bank Rate, in December 2021, to fight the
  inflation that followed the pandemic and the energy shock after Russia's invasion of Ukraine. The
  crash phase ends in October 2023, when long-dated gilt yields reached their highest month end
  since the rises began and long-dated gilt prices their lowest. The window is shorter than the
  others, so the five-year rule of ADR 0003 no longer applies to every window.

## Consequences

- Every figure is a model, and it will differ from a gilt fund's own record: real indexes hold
  particular gilts in the amounts issued, the curve is the Bank's fitted estimate and is flat beyond
  20 years, so most long rungs move with the 20-year yield alone, gilts issued before 1982 all carry
  that year's coupons, float adjustment for the Bank's own holdings is ignored, and the 1 to 5-year
  indexes share the up-to-5-years model.
- The ladders' returns start in April 1992, the month after the 20-year point begins, and the
  up-to-5-years model in January 1994, so all four crash windows are covered.
- The Covid window runs to December 2024, so it includes 2022; a card reports the worst fall in the
  crash phase only, and the 2022-23 window shows the later fall on its own.
- The 10-year gilt and the Bank Rate index holdings are retired; splits in an open session that
  still hold them drop them, as for any holding no longer listed.
