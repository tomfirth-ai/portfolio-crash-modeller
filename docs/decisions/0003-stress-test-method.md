# 3. Stress-test method: monthly, in pounds, through fixed crash windows

Date: 15 October 2026. Status: accepted. Extended in Slice 2 with a second way of managing a split,
an explanation of each fall and a third crash (see the end). Amended by
[ADR 0005](0005-real-funds-modelled.md): splits now hold funds and indexes, and fund charges are
taken off.

## Context

The stress test compares splits through real crashes. The comparison has to be fair (every split
measured the same way over the same months), in the investor's own currency, built only from data the
project may use, and explainable in plain words.

## Decision

- **Monthly data, keyed by calendar month.** Sources label month ends differently (a trading day, a
  calendar day, or the month alone), so every series is keyed by `YYYY-MM` and series cannot have
  gaps. Figures come from month-end values, so falls within a month can be deeper than shown.
- **Building blocks**, all as monthly total returns:
  - *Global shares (developed markets)*: the Kenneth R. French Developed market return
    (`Mkt-RF + RF`), in US dollars, from July 1990, fetched at runtime (ADR 0002).
  - *US shares*: the French US market return, in US dollars, fetched at runtime.
  - *UK government bonds (10-year)*: computed from the Bank of England's month-end 10-year nominal
    par gilt yield (series `IUMMNPY`, from December 1993). Each month holds a new 10-year bond
    bought at par, revalued a month later at the new yield with semi-annual compounding, plus a
    month's coupon:
    `r = y[t-1]/1200 + (y[t-1]/y[t] - 1) * (1 - (1 + y[t]/200) ** -(2 * (10 - 1/12)))`.
    This is the formula of Swinkels' international government bond returns dataset
    (doi:10.25397/eur.8152748; method in Swinkels (2019), *Data* 4(3), 91). On the Bank's yields it
    reproduced his published UK returns for 2012 to 2022, where he used the same input, to within
    3e-16.
  - *Cash (Bank Rate)*: interest accrues each calendar day at Bank Rate and is credited monthly,
    `sum over the month's days of rate / 100 / 365`. Bank Rate is the Bank of England's policy
    rate, a yardstick for cash rather than what any account pays.
- **Into pounds.** Dollar returns are converted at month-end US dollars per pound from the Federal
  Reserve's H.10 release, the last day with a rate in each month:
  `r_GBP = (1 + r_USD) * X[t-1] / X[t] - 1`. The returns multiply, never add; the dropped cross
  term is large in a crash. H.10 rates are noon New York rates, a few hours away from the month-end
  closes behind the share returns, which adds small timing noise.
- **Kept at its weights, by default.** Each split is put back to its weights at every month end,
  much as ready-made multi-asset funds keep a fixed mix, so results describe the split as designed.
  Costs, fees and taxes are left out. Leaving a split alone to drift was added in Slice 2 (below).
- **Fixed crash windows from events**, shared by every split:

  | Crash | Worth 100 at the end of | Crash phase ends | Window ends |
  |---|---|---|---|
  | 2000-03 dot-com crash | February 2000 | March 2003 | February 2005 |
  | 2007-09 financial crisis | June 2007 | June 2009 | June 2012 |
  | 2020 Covid crash | December 2019 | June 2020 | December 2024 |

  The starts come before each crash broke (the technology bubble bursting in March 2000; the credit
  crunch in August 2007; the first reported cases at the end of 2019). The 2007-09 and 2020 crash
  phases end with the recessions' troughs; the dot-com crash phase ends with the start of the Iraq
  war in March 2003, after the US recession of 2001, the September 2001 attacks and the accounting
  scandals of 2002. The windows are not
  anchored on any index's peak, so nothing about them depends on data that may change or may not be
  committed.
- **A split gets a result only if every block it holds covers the whole window.** Otherwise it says
  which data it lacks, rather than shortening the window or treating missing months as zero.
- **What is measured**, from a split's month-end values through the window:
  - the *worst fall*: the biggest drop from a high point to a low point that comes in the crash
    phase, measured from the latest month at that high (which may be the start);
  - *months to the bottom*, from that high point to the low point;
  - *months to recover*, from the low point back to the high point; if that does not happen by the
    end of the window, the recovery is unknown, never zero;
  - the *value at the end* of the window of £100 at the start;
  - flags for a bottom in the last month of the crash phase (it may not have finished falling) and
    for a deeper low after the crash phase and before recovery.
- **In pounds, before inflation.** Inflation does not change which split ended a window ahead,
  because every split faces the same prices, and it matters little over the months of a crash. Over
  five years it matters more, which the page says. Inflation arrives with tracking.

## Consequences

- The figures will not match published sterling index returns exactly: the index definitions, the
  exchange-rate timing and the monthly frequency all differ.
- The share figures change slightly from month to month, because the French library rebuilds its
  history with each update. The app shows the data vintage.
- No figure derived from the French data appears in any committed file. Tests, docs and examples use
  synthetic numbers.

## Slice 2 additions

- **Left alone, as well as kept at its weights.** A visitor can also see a split bought once and
  never rebalanced, so that whatever does well grows to a larger share. The engine values each
  holding separately in both cases: every month a holding gains its return on the amount in it at
  the start of the month, and the split is the sum of its holdings.
- **What drove a fall.** From the high to the bottom, the change in a split's value is exactly the
  sum of its holdings' gains over the months in between, so each holding's share of the fall is its
  own gains as a fraction of the value at the high. The shares add up to the fall, with no
  remainder to explain away.
- **What the pound did.** For a split holding shares, the same split is also run with the share
  returns left in US dollars, while bonds and cash stay in pounds. The difference shows what the
  pound's moves against the dollar did to a sterling investor. It is exact for US shares. For global
  shares it is approximate: that index is priced in dollars but holds UK and other non-US
  companies, so its dollar returns still carry their own currencies' moves, and its UK part gains a
  pound-dollar effect a sterling investor never had. It is a what-if, not a hedged return: hedging
  would also earn or pay the interest-rate gap between the two currencies.
- **A third crash.** The dot-com crash joins the two windows above, measured the same way. Every
  block covers it: the developed-markets returns start in July 1990 and the gilt yield in December
  1993.
