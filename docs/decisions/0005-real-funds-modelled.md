# 5. Real funds, modelled from open data

Date: 16 October 2026. Status: accepted. Amends [ADR 0003](0003-stress-test-method.md): splits hold
funds and indexes instead of four building blocks, and fund charges are taken off.

## Context

Splits of four generic building blocks are too general for a real investor, who wants to see how
the funds they hold or are weighing up would have come through a crash: a FTSE All-World tracker,
an S&P 500 tracker, a money market fund. Two constraints shape how:

- **No real fund or index history can be shown.** Index providers (MSCI, FTSE Russell, S&P, Bloomberg)
  and fund managers license their index levels and prices; none of them may be committed, cached or
  shown on the hosted app (ADR 0002). Most UK-listed trackers also launched after 2008, so their own
  records miss the crashes anyway.
- **The Kenneth R. French Data Library publishes more than market returns.** Its size and
  size-by-value portfolios come with each portfolio's number of firms and average firm size every
  month. Multiplying the two gives each portfolio's market value, so indexes defined by company size
  can be rebuilt from them, with weights that change month by month as markets grow and shrink.

## Decision

- **A split holds funds and indexes.** Each fund is linked to a model of the index it tracks, and a
  visitor can also hold the index itself, before any charges. The examples hold indexes only, so no
  example names a fund.
- **Index models**, from French files fetched at runtime (ADR 0002) and the open data stored with
  the app, all as monthly total returns in pounds, converted from dollars as in ADR 0003:
  - *S&P 500*: the 500 largest US companies. Starting from the largest tenth of the market by size,
    whole tenths are added until 500 firms are reached, and the last tenth counts in proportion to
    the firms needed from it. Each tenth is weighted by its market value. Source:
    `Portfolios_Formed_on_ME`, built from CRSP.
  - *MSCI World*: the "big" companies of 23 developed countries, those making up the top 90% of
    their region's market value each June, which is close to the large and mid-sized companies an
    index of that kind covers. Source: `Developed_6_Portfolios_ME_BE-ME`.
  - *FTSE All-World*: the same for developed and emerging markets together, each part weighted by
    its market value every month, so no share for emerging markets is assumed. In emerging markets
    the big companies are the top 90% of each country's market value. Sources: the developed and
    `Emerging_Markets_6_Portfolios_ME_BE-ME` files.
  - *FTSE Global All Cap*: as FTSE All-World, but with companies of every size.
  - *Sterling money market*: the cash returns on Bank Rate already stored (ADR 0003).
  - *UK gilts*: the 10-year par gilt model of ADR 0003, until gilt funds arrive in Slice 4.
- **Weights from the same month.** The number of firms and average size French reports for a month
  are taken as the portfolio's size at the start of that month, so they weight that month's returns.
  Weighting two of the library's size portfolios this way rebuilds the combined portfolio it
  publishes, to rounding.
- **Fund charges.** Each month a fund's return is reduced by a twelfth of its yearly ongoing charge:
  `r_fund = (1 + r_index) * (1 - charge / 12) - 1`. The charge is the one published in the fund's key
  information document, typed in by hand with the document's date. Tax withheld on dividends, dealing
  costs, platform charges and any gap between a fund and its index beyond its charge are not
  modelled. A split that holds the index itself bears no charge.
- **Which funds are listed.** For each index the app models, every tracker that UK investors can
  buy from Amundi, Fidelity, HSBC, Invesco, iShares, L&G, SPDR, UBS, Vanguard and Xtrackers, listed
  alphabetically: for an ETF, each share class that trades in pounds on the London Stock Exchange,
  under its London ticker; for an index fund, the class UK platforms usually sell. Hedged classes,
  and money market funds that are managed actively rather than tracking SONIA, are left out. Each
  line of `src/crashmodel/data/funds.csv` holds a fund's index, manager, name, ticker, ongoing charge
  and share-class launch month, with the date of the key information document they come from. There
  are no ISINs, and nothing is copied by script.
- **The fund list and the privacy scan.** A public fund's name or ticker may also be an entry on the
  owner's denylist, so the scan reads the fund list for numbers and dates only, and only while the
  file has exactly the list's shape. Anything else in it is scanned in full, and tests check that
  every line names a listed index and manager.
- **How funds are named.** Names are used only to identify the index or fund a model describes:
  - every label says "(modelled)";
  - each page that names a fund says the app is not affiliated with, sponsored or endorsed by any
    index provider or fund manager, and gives the owners of the trade marks;
  - charts are captioned as simulated past performance, not the fund's own returns;
  - no logos, and never "replica", "clone" or "stand-in", which would present a model as an imitation
    of the fund;
  - no claim of how closely a model follows its index or fund.
- **Funds that launched after a crash began.** The card names them with their launch months, and
  says that their figures, like every figure in the app, come from a model of the index each
  tracks, after its charge.

## Consequences

- Every figure is a model. It will differ from a fund's own record: a French portfolio is cut by
  company size, not chosen by an index committee or adjusted for shares that are not freely traded;
  new companies join only at the June re-sort; the country lists differ a little from the index
  providers'; and dividends are counted before tax.
- The "big" cut is set in June each year, so a fast-growing company can sit in the smaller group for
  a few months. Index rules differ in the same way at the edges.
- The models depend on the runtime French files in the same way as the shares before them: if a file
  cannot be fetched, the splits holding a fund that needs it say so, and the others still run.
- The share figures still change slightly with each monthly update of the French library, and the app
  shows each file's vintage.
- Later slices add gilt funds built from the Bank of England's yield curve, more markets, and
  index-linked and global bond funds, under the same rules. Real London closing prices may follow on
  the Track page only if the London Stock Exchange approves it in writing.
