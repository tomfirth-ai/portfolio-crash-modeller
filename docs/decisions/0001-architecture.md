# 1. Architecture: a journey-first app over a pure engine and one data store

Date: 14 October 2026. Status: accepted.

## Context

The tool helps an investor design a portfolio split, stress-test it through real crashes, decide on
one and then track it. It is also a public example of how the author builds software, so clarity,
correctness and privacy matter more than feature count.

## Decision

- **The four-step journey is the spine of the product.** Design, Stress-test, Decide and Track are
  defined once in a registry that every page reads from. Pages say things in words first, then
  numbers, then charts. Amended 16 October 2026: on Stress-test the chart comes first, in one panel
  with the crash picker, so it stays in place while a visitor flicks between crashes; each split's
  story and figures follow.
- **Three layers with one-way dependencies.**
  - `engine/` holds every financial calculation as pure, typed functions with tests.
  - `data/` fetches, validates and stores series, and owns all I/O.
  - `app/` is presentation only: thin Streamlit pages that draw the output of unit-tested
    presenters.
- **YAML for definitions, one store for data.** Portfolios, instruments, strategies, episodes and
  scenarios are YAML files validated by pydantic. Observations live in a single SQLite store, built
  from committed CSV files plus runtime fetches, and the app reads only through the store's API.
  Derived values such as portfolio values and peaks are computed when read, never stored.
- **Provenance travels with every series**: source, licence, currency, return basis, frequency and
  whether each value is observed, carried forward, a proxy or synthetic.
- **Monthly data for stress tests, daily data for tracking.** Free long-run history is monthly, and
  one convention is enforced per series.
- **The engine is currency-agnostic, with sterling as the default.** The currency lens (how a
  falling pound cushions overseas holdings) works for any base currency with FX data.
- **Hosted and local modes.**
  - **Hosted (the public demo):** the store is read-only and visitors' entries live only in their
    session.
  - **Local:** the store is writable, and personal configuration lives outside the repository.

## Consequences

- Each layer can be tested on its own, and the engine has no idea Streamlit exists.
- Adding a page means adding presenter functions and a thin page script, not new logic.
- One store means no drift between copies of the same data, which was the main weakness of the
  spreadsheet-based tool this project replaces.
