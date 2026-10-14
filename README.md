# Portfolio crash modeller

**How would your investments have coped with a crash?** Try out different ways to split your
money, see how each would have done in real crashes such as 2008 and 2020, then track the one you
choose.

> **Not investment advice.** This is a learning and portfolio project. Past performance, real or
> simulated, is not a reliable indicator of future results.

## The journey

1. **Design** a split: shares, bonds and cash in the proportions you have in mind.
2. **Stress-test** it through real historical crashes, side by side with other splits.
3. **Decide** on one and lock it in with a start date and an amount.
4. **Track** how it is doing against inflation, cash and the splits you did not choose.

## Status

Early build. The foundations are in place: strict tooling, privacy guards, CI and the app shell.
The four steps are being built in order, and a live demo link will appear here.

## Run it locally

You need [uv](https://docs.astral.sh/uv/), which also installs the right Python.

```sh
uv sync
uv run streamlit run streamlit_app.py
```

## Develop

```sh
uv run pre-commit install            # once: installs the commit and push hooks
uv run pre-commit run --all-files    # lint, format, types, style, hygiene and privacy checks
uv run pytest                        # tests, with network access blocked and 100% coverage
```

Together the last two run everything CI runs. The hooks also run a privacy scan, which compares
staged files, commit messages and every commit you push with a denylist of personal details that
you keep outside the repository, at `~/.config/crashmodel/denylist.txt` (one entry per line, with
`#` for comment lines). It matches names, tickers, amounts and dates in the common forms they are
written, and refuses to run without a denylist. It is a safety net, not a guarantee, so still
review what you commit.

## Licence

The code is released under the [MIT licence](LICENSE). Data has its own terms: see
[DATA_LICENCES.md](DATA_LICENCES.md).
