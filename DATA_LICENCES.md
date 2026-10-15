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

Some data is fetched when the app runs and is never stored in this repository, either because its
publisher allows use but not redistribution, or because it has to be up to date. The app's Data
sources page lists these sources and checks that each one can be reached.
