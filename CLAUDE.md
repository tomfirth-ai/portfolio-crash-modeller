# Portfolio crash modeller: rules for Claude Code

Private context, when present, lives in the git-ignored `CLAUDE.local.md` and `private/`.

## Hard rules
- This is a public repository. Never commit personal data: no real holdings, unit counts, amounts, account
  or provider names, or anyone's portfolio details. Demo portfolios in `config/` use illustrative weights.
- Commit only freely redistributable data, with its source and licence recorded next to it. Never commit
  proprietary index values (for example MSCI, FTSE Russell or S&P) or data downloaded via FRED or Yahoo.
  Statistics computed from data that may not be committed never appear in committed files.
- Test fixtures and golden values are hand-worked, round-number synthetic data.
- Small, well-described commits. Stage files by name. Never commit secrets, caches, databases or anything
  under `private/` or `local/`.
- Work in plan mode for any new phase: propose, wait for approval, then build.

## Product
- The user journey is the spine: **Design** a split, **Stress-test** it through real crashes, **Decide** and
  lock one in, **Track** it. Every page serves that story: words first, then numbers, then charts.
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
