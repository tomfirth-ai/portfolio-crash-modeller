# US dollars per pound at the end of each month

- **File:** `usd_per_gbp.csv`, with the header `month,usd_per_gbp` and one row per month, written YYYY-MM.
- **Publisher:** Board of Governors of the Federal Reserve System.
- **Dataset:** H.10 Foreign Exchange Rates: United Kingdom pound, US dollars per pound.
- **Where:** https://www.federalreserve.gov/releases/h10/
- **Licence:** Public domain, https://www.federalreserve.gov/disclaimer.htm
- **Attribution:** Source: Board of Governors of the Federal Reserve System, H.10 release.
- **Retrieved:** 2026-10-15. Months from 2026-10 on are left out, because they had not ended.
- **Downloaded files:**
  - https://www.federalreserve.gov/releases/h10/data/FRB_h10_xml.zip, SHA-256 `c5b4309593cb217a3bba7d3951621299ff018ed7b8a9554790f52c8e8a5881fd`
- **How it was made:** The last daily rate in each calendar month, from series RXI$US_N.B.UK in the release's XML file (H10_data.xml), written to 4 decimal places as published.
