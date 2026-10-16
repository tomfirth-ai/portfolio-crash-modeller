# Portfolio crash modeller: rules for Claude Code

Private context, when present, lives in the git-ignored `CLAUDE.local.md` and `private/`.

## Hard rules
- This is a public repository. Never commit personal data: no real holdings, unit counts, amounts, account
  or provider names, or anyone's portfolio details. Example and demo portfolios use illustrative weights.
- Commit only freely redistributable data, with its source and licence recorded next to it. Never commit
  proprietary index values (for example MSCI, FTSE Russell or S&P) or data downloaded via FRED or Yahoo.
  Statistics computed from data that may not be committed never appear in committed text: code, tests,
  docs, commit messages or screenshots. That includes any figure read off the live app.
- Test fixtures and golden values are hand-worked, round-number synthetic data.
- Small, well-described commits. Stage files by name. Never commit secrets, caches, databases or anything
  under `private/` or `local/`.
- Build from the approved roadmap (`docs/roadmap.md`), one slice at a time. Each slice ends with something
  usable, and the owner tries it on the live app before the next starts. New scope, and any change to data
  sources, licences, the privacy tools or the method, goes back to the owner as a plan.

## Product
- The user journey is the spine: **Design** a split, **Stress-test** it through real crashes, **Decide** and
  lock one in, **Track** it. Every page serves that story: words first, then numbers, then charts. The
  exception is Stress-test, whose chart sits under the crash picker so it stays put while a visitor
  flicks between crashes.
- "Not investment advice" appears in the README and on every page. Never describe a split as best, safe,
  recommended or suitable.

## Code standard
- Financial calculations live in `engine/` as pure, typed functions, and every one has pytest tests.
- `app/` is presentation only. User-facing text comes from presenters that are unit tested.
- mypy strict, ruff with pydocstyle, named constants instead of magic numbers, I/O injected at the edges,
  and docstrings that explain the finance in plain words.
- Add a dependency only when it is first used.

## Style
- British English in docs and UI text.
- No en or em dashes, or similar lookalike characters, anywhere in the repository.
