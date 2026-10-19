# The privacy guard

This repository is public, and its maintainer works on it alongside private files. A privacy scan
stops personal details from reaching the git history by accident.

## What it checks

The pre-commit hooks scan the staged files, each commit message and every commit about to be pushed
against a denylist of personal details: names, tickers, amounts, dates and email addresses. The
denylist is kept outside the repository, at `~/.config/crashmodel/denylist.txt` by default, with one
entry per line and `#` for comment lines. The scan matches each entry in the common forms it is
written, such as an amount with or without its thousands separators, and reports only line
numbers, never the matching text. CI runs a separate secret scan of the full history.

Some files hold public figures or names that could match an entry by chance:

- `uv.lock` and the stored monthly series are scanned for words only, since their figures can match
  an amount by chance;
- in the fund list, the fund names and tickers are left out of the word scan, since a public fund
  name could match an entry, while every other field must hold a listed index or fund manager.

## Running it

Without a denylist the scan refuses to run, so a contributor without one skips its three hooks:

```sh
SKIP=privacy-staged,privacy-message,privacy-push git commit
```

`uv run python -m tools.privacy_scan --all-history` scans every commit, tag and branch name.

The scan is a safety net, not a guarantee: what is committed is still reviewed by eye.
