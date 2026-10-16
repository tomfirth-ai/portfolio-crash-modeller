# SONIA (Sterling Overnight Index Average) and Official Bank Rate, daily

- **Files**, each with one row per month, written YYYY-MM:
  - `cash_return.csv`, with the header `month,cash_return`: The monthly return on cash earning SONIA, compounded daily, and Bank Rate before SONIA began. Daily SONIA (series IUDSOIA) from its first day, 2 January 1997, and the daily Official Bank Rate (series IUDBEDR) before it, from the Bank's Interactive Database, turned into a monthly return on cash. Each calendar day earns the rate in force that day, rate / 100 / 365, compounded daily. The first month is the first with a rate on its first day. The last month is the last whose final rate had been published. The returns are worked out by this project, not by the Bank.
  - `overnight_rate.csv`, with the header `month,overnight_rate`: The overnight rate at the end of each month, SONIA or Bank Rate before it, in percent. Daily SONIA (series IUDSOIA) from its first day, 2 January 1997, and the daily Official Bank Rate (series IUDBEDR) before it, from the Bank's Interactive Database: the last rate in each calendar month, written to 4 decimal places.
- **Publisher:** Bank of England.
- **Dataset:** SONIA (Sterling Overnight Index Average) and Official Bank Rate, daily.
- **Where:** https://www.bankofengland.co.uk/boeapps/database/
- **Licence:** Open Government Licence v3.0, https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
- **Attribution:** SONIA and/or SONIA Compounded Index data licensed under the Open Government Licence v3.0 and copyright the Governor and Company of the Bank of England. The trade marks "Bank of England" and "SONIA" are registered trade marks of the Bank of England. Contains public sector information licensed under the Open Government Licence v3.0.
- **Retrieved:** 2026-10-16. Months from 2026-10 on are left out, because they had not ended.
- **Downloaded files:**
  - https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01%2FJan%2F1975&Dateto=now&SeriesCodes=IUDBEDR&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N, SHA-256 `bf022bf62a4e4d1642a15a97e4fb0bf61c1d505ca4bfa7964e521a3c1be0a3ac`
  - https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01%2FJan%2F1975&Dateto=now&SeriesCodes=IUDSOIA&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N, SHA-256 `6236a53d5d2ca9d71b05e8ac52d764cf9d7c98f972ad2e6eb91e0280265be10b`
