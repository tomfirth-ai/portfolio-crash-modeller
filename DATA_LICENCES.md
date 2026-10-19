# Data licences

The code in this repository is released under the [MIT licence](LICENSE). That licence covers code
only. It does not cover data.

## Committed data

Each series lives in `src/crashmodel/data/reference/<source>/`, with a `SOURCE.md` in each folder
that records how each file was made, the publisher, licence, attribution, retrieval date and the
SHA-256 of every file downloaded.
`tools/build_reference_data.py` rebuilds them from the publishers' own files. Only freely
redistributable data is ever committed.

| Series | Publisher | Licence | Attribution |
|---|---|---|---|
| US dollars per pound, month end (`fed-h10/`) | Board of Governors of the Federal Reserve System, H.10 release | Public domain ([terms](https://www.federalreserve.gov/disclaimer.htm)) | Source: Board of Governors of the Federal Reserve System, H.10 release. |
| 5, 10 and 20-year nominal zero-coupon gilt yields and the 5-year nominal par gilt yield, month end (`boe-yield-curve/`) | Bank of England | [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) | Contains public sector information licensed under the Open Government Licence v3.0. |
| Monthly return on cash earning SONIA, with Bank Rate before SONIA began, and Bank Rate at each month end (`boe-sterling-cash/`) | Bank of England, derived from SONIA and Official Bank Rate | [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) | SONIA and/or SONIA Compounded Index data licensed under the Open Government Licence v3.0 and copyright the Governor and Company of the Bank of England. The trade marks "Bank of England" and "SONIA" are registered trade marks of the Bank of England. Contains public sector information licensed under the Open Government Licence v3.0. |

The gilt models are worked out from these series ([ADR 0006](docs/decisions/0006-gilts-and-sonia.md)).
The up-to-5-years model's 5-year gilt uses the formula of Swinkels' international government bond
returns dataset (doi:10.25397/eur.8152748, CC BY 4.0), described in Swinkels (2019), *Data* 4(3),
91. Only the method is used; none of that dataset is stored here.

## Data fetched at runtime

The share models ([ADR 0005](docs/decisions/0005-real-funds-modelled.md)) are built from the
[Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)'s
portfolios of companies grouped by size: `Portfolios_Formed_on_ME` (US companies in tenths by market
value, built from CRSP), and `Developed_6_Portfolios_ME_BE-ME` and
`Emerging_Markets_6_Portfolios_ME_BE-ME` (big and small companies, built from Bloomberg). The app
fetches a file only when a split needs it. The files are free to download, but no licence is given
to redistribute them, so the app keeps them in memory only, and never writes them to disk or commits
them ([ADR 0002](docs/decisions/0002-hosted-data-mode.md)). It refreshes each file once a day and,
if a refresh fails, keeps using the copy it has. Nothing computed from them
appears in this repository. The app's Data sources page checks that each file can be reached.

Fund names, tickers, ongoing charges and launch dates are facts typed in by hand from each fund's
key information document, with the document's date, into
[`src/crashmodel/data/funds.csv`](src/crashmodel/data/funds.csv). No index values or fund prices are
used.
