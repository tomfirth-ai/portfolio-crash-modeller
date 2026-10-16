# Official Bank Rate, daily

- **Files**, each with one row per month, written YYYY-MM:
  - `cash_return.csv`, with the header `month,cash_return`: The monthly return on cash earning Bank Rate, accrued daily. The daily Official Bank Rate (series IUDBEDR) from the Bank's Interactive Database, turned into a monthly return on cash. Each calendar day earns the rate in force that day, rate / 100 / 365, compounded daily. The first month is the first with a rate on its first day.
- **Publisher:** Bank of England.
- **Dataset:** Official Bank Rate, daily.
- **Where:** https://www.bankofengland.co.uk/boeapps/database/
- **Licence:** Open Government Licence v3.0, https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
- **Attribution:** Contains public sector information licensed under the Open Government Licence v3.0.
- **Retrieved:** 2026-10-16. Months from 2026-10 on are left out, because they had not ended.
- **Downloaded files:**
  - https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01%2FJan%2F1975&Dateto=now&SeriesCodes=IUDBEDR&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N, SHA-256 `bf022bf62a4e4d1642a15a97e4fb0bf61c1d505ca4bfa7964e521a3c1be0a3ac`
