# The monthly return on cash earning Bank Rate, accrued daily

- **File:** `cash_return.csv`, with the header `month,cash_return` and one row per month, written YYYY-MM.
- **Publisher:** Bank of England.
- **Dataset:** Official Bank Rate, daily.
- **Where:** https://www.bankofengland.co.uk/boeapps/database/
- **Licence:** Open Government Licence v3.0, https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
- **Attribution:** Contains public sector information licensed under the Open Government Licence v3.0.
- **Retrieved:** 2026-10-15. Months from 2026-10 on are left out, because they had not ended.
- **Downloaded files:**
  - https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01%2FJan%2F1975&Dateto=now&SeriesCodes=IUDBEDR&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N, SHA-256 `574177f82d1c4346b307df9b4ed13c337c5cffd06862770ae01e1420e502d74c`
- **How it was made:** The daily Official Bank Rate (series IUDBEDR) from the Bank's Interactive Database, turned into a monthly return on cash: interest accrues each calendar day at the rate in force that day, rate / 100 / 365, and is credited at the month end. The first month is the first with a rate on its first day.
