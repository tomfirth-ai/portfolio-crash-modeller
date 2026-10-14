# 2. Hosted data mode: commit only open data, fetch academic equity history at runtime

Date: 14 October 2026. Status: accepted, and confirmed from the hosted app (see the end).

## Context

The public demo must compare portfolio splits through real crashes such as 2008 and 2020, with no
API keys. Licence research found:

- **No open monthly equity history.** There is no openly licensed monthly equity history for the
  world, US or UK markets before ETFs existed.
- **Yahoo Finance.** Its terms prohibit automated collection and redistribution, and shared cloud
  hosts are rate-limited.
- **FRED.** Its terms prohibit storing or caching its content, even public-domain series, so data
  must come from the original publishers instead.
- **Open data that can be committed.** Government bond returns (Swinkels, CC BY 4.0), a global
  multi-asset market portfolio (Doeswijk, Schmalz and Swinkels, CC BY 4.0), and official exchange
  rates, interest rates and inflation from the Federal Reserve Board, the Bank of England, the ONS,
  the BLS, the BIS and the ECB.

## Decision

- **Commit only freely redistributable series**, downloaded from their original publishers, with
  the publisher, licence and required attribution recorded beside each file.
- **Fetch academic equity history at runtime on the hosted demo.** The Kenneth R. French Data
  Library is freely downloadable and nothing in its terms bars automated access. It is fetched
  when needed, held in memory, never committed and always attributed with its data vintage.
- **Yahoo Finance is local only**, an optional extra that is off by default. Its terms expressly
  prohibit automated collection and redistribution, which the hosted app would otherwise do on a
  visitor's behalf.
- **When a runtime fetch fails**, the app says so and falls back to committed open data plus clearly
  labelled synthetic series, so it always works.

## Consequences

- The public demo shows real crash history without redistributing any restricted data.
- Equity-dependent features (value and growth sleeves, the growth-led test) need the runtime fetch,
  and the app labels them when it is unavailable.
- Statistics computed from runtime-only data never appear in committed files.

## Connectivity from the hosted app

On 14 October 2026, after the first deployment to Streamlit Community Cloud, the app's Data sources
page reported both runtime sources reachable from Cloud: the Kenneth R. French Data Library and the
Federal Reserve Board H.10 release. The decision stands.

One local check that day timed out against the French library at the 10 second limit, so runtime
fetches must keep failing gracefully, as described above.
