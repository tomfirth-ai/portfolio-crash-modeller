# Data licences

The code in this repository is released under the [MIT licence](LICENSE). That licence covers code
only. It does not cover data.

## Committed data

Each series lives in `src/crashmodel/data/reference/<source>/`, with a `SOURCE.md` beside it that
records the publisher, licence, attribution, retrieval date and the SHA-256 of every file downloaded.
`tools/build_reference_data.py` rebuilds them from the publishers' own files. Only freely
redistributable data is ever committed.

| Series | Publisher | Licence | Attribution |
|---|---|---|---|
| US dollars per pound, month end (`fed-h10/`) | Board of Governors of the Federal Reserve System, H.10 release | Public domain ([terms](https://www.federalreserve.gov/disclaimer.htm)) | Source: Board of Governors of the Federal Reserve System, H.10 release. |
| 10-year nominal par gilt yield, month end (`boe-gilt-yield/`) | Bank of England | [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) | Contains public sector information licensed under the Open Government Licence v3.0. |
| Monthly return on cash earning Bank Rate (`boe-bank-rate/`) | Bank of England, derived from Official Bank Rate | [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) | Contains public sector information licensed under the Open Government Licence v3.0. |

UK government bond returns are computed from the gilt yield with the formula of Swinkels'
international government bond returns dataset (doi:10.25397/eur.8152748, CC BY 4.0), described in
Swinkels (2019), *Data* 4(3), 91. Only the method is used; none of that dataset is stored here.

## Data fetched at runtime

The share models ([ADR 0005](docs/decisions/0005-real-funds-modelled.md)) are built from the
[Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)'s
portfolios of companies grouped by size: `Portfolios_Formed_on_ME` (US companies in tenths by market
value, built from CRSP), and `Developed_6_Portfolios_ME_BE-ME` and
`Emerging_Markets_6_Portfolios_ME_BE-ME` (big and small companies, built from Bloomberg). The app
fetches a file only when a split needs it. The files are free to download, but no licence is given
to redistribute them, so the app keeps them in memory for up to a day, and never writes them to disk
or commits them ([ADR 0002](docs/decisions/0002-hosted-data-mode.md)). Nothing computed from them
appears in this repository. The app's Data sources page checks that each file can be reached.

Fund names, tickers, ongoing charges and launch dates are facts typed in by hand from each fund's
key information document, with the document's date, into
[`src/crashmodel/data/funds.csv`](src/crashmodel/data/funds.csv). No index values or fund prices are
used.
