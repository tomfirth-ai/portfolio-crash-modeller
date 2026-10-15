# 4. Build in vertical slices, and what that changes in ADRs 0001 and 0002

Date: 15 October 2026. Status: accepted.

## Context

The first deployment was the journey shell: a Home page describing four steps that did not exist yet.
The original plan built in layers (the whole engine, then all the data, then the pages), so nothing
usable would have reached the live app for several more phases. A tool that cannot be tried cannot
be judged, by its owner or by anyone else.

## Decision

- **Build in vertical slices**, as listed in the [roadmap](../roadmap.md). Each slice takes a thin
  path through engine, data and pages, ends with something a visitor can use on the live app, and is
  tried by the owner there before the next starts.
- **Defer what no slice needs yet.** The YAML definitions and the single SQLite store in ADR 0001 wait
  until a slice needs them (tracking, or local mode). Until then the committed reference series are
  small CSV files inside the package, read through one module.
- **Fallback in stages.** ADR 0002 promises labelled stand-in series when a runtime fetch fails. Slice 1
  shows a clear banner and a "Try again" button instead, and splits without shares still get results.
  The stand-ins arrive with Slice 2.
- **Corrections to ADR 0002's list of committable data**, after checking each source:
  - The global market portfolio of Doeswijk and Swinkels is not used. In its CC BY file the
    non-dollar currency blocks appear faulty, and it gives no breakdown by asset class, so it cannot
    stand in for shares. (ADR 0002 also named Schmalz as an author, which the dataset record does
    not.)
  - Swinkels' government bond returns are not committed. His UK returns before 2012 are built from a
    Bank of England spreadsheet that sits outside the Bank's open licence. UK government bond returns
    are computed instead from the Bank's 10-year par gilt yield, which is openly licensed, using his
    published method.

## Consequences

- Every slice is reviewed on the real host, so problems with data, hosting and usability show up
  early rather than at the end.
- Some architecture arrives later than first planned, and is added when a slice needs it.
