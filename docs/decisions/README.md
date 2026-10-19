# Decision records

Each record says why the app works as it does, at the time it was decided. Later records amend
earlier ones rather than rewriting them, so read a record together with those that amend it. The
method as it stands today is set out in plain words on the app's "How it works" page.

| Record | Decision | Amended by |
|---|---|---|
| [0001](0001-architecture.md) | A journey-first app over a pure engine; three layers with one-way dependencies | 0004 (the YAML definitions and the data store are deferred) |
| [0002](0002-hosted-data-mode.md) | Commit only open data; fetch academic share history when the app runs | 0004 (committable data corrected, fallback replaced), note of 19 October 2026 |
| [0003](0003-stress-test-method.md) | Monthly figures, in pounds, through fixed crash windows | 0005 (funds and charges), 0006 (gilts and cash, the 2022-23 crash) |
| [0004](0004-vertical-slices.md) | Build in vertical slices, each usable on the live app | 0006 (gilts), notes of 19 October 2026 (no stand-ins; public from v0.1) |
| [0005](0005-real-funds-modelled.md) | Real funds, each modelled from open data after its charges | 0006 (gilt and cash models) |
| [0006](0006-gilts-and-sonia.md) | Gilts from the Bank of England's yield curve, cash on SONIA, and the 2022-23 bond crash | |
