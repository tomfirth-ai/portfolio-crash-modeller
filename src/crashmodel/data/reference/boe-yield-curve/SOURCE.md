# Yields from British Government Securities: nominal zero-coupon and par yields, end of month

- **Files**, each with one row per month, written YYYY-MM:
  - `five_year_zero_yield.csv`, with the header `month,five_year_zero_yield`: The 5-year nominal zero-coupon gilt yield at the end of each month, continuously compounded, in percent. The end-of-month yield (series IUMSNZC) from the Bank's Interactive Database, written to 4 decimal places. The Bank drops trailing zeros.
  - `ten_year_zero_yield.csv`, with the header `month,ten_year_zero_yield`: The 10-year nominal zero-coupon gilt yield at the end of each month, continuously compounded, in percent. The end-of-month yield (series IUMMNZC) from the Bank's Interactive Database, written to 4 decimal places. The Bank drops trailing zeros.
  - `twenty_year_zero_yield.csv`, with the header `month,twenty_year_zero_yield`: The 20-year nominal zero-coupon gilt yield at the end of each month, continuously compounded, in percent. The end-of-month yield (series IUMLNZC) from the Bank's Interactive Database, written to 4 decimal places. The Bank drops trailing zeros.
  - `five_year_par_yield.csv`, with the header `month,five_year_par_yield`: The 5-year nominal par gilt yield at the end of each month, in percent. The end-of-month yield (series IUMSNPY) from the Bank's Interactive Database, written to 4 decimal places. The Bank drops trailing zeros.
- **Publisher:** Bank of England.
- **Dataset:** Yields from British Government Securities: nominal zero-coupon and par yields, end of month.
- **Where:** https://www.bankofengland.co.uk/boeapps/database/
- **Licence:** Open Government Licence v3.0, https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
- **Attribution:** Contains public sector information licensed under the Open Government Licence v3.0.
- **Retrieved:** 2026-10-16. Months from 2026-10 on are left out, because they had not ended.
- **Downloaded files:**
  - https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01%2FJan%2F1975&Dateto=now&SeriesCodes=IUMSNZC&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N, SHA-256 `fcb3ed780817bf229758f539cda0bc5e172936e045dd6c66c530803fd25e08f7`
  - https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01%2FJan%2F1975&Dateto=now&SeriesCodes=IUMMNZC&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N, SHA-256 `3543b757d49c7e310323d3f68242eb0ba44cb0951c74b325cdbd60e1be8549b7`
  - https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01%2FJan%2F1975&Dateto=now&SeriesCodes=IUMLNZC&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N, SHA-256 `de66ec1d9abe54cb041eb0750aaa6af809368f7d806d7d8d94b722bc6d09f3f3`
  - https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01%2FJan%2F1975&Dateto=now&SeriesCodes=IUMSNPY&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N, SHA-256 `60fa2f1b6090e3ed5b55a86613f19eeff560ca2d8c0fc6d529e0aa88a86ef8e7`
