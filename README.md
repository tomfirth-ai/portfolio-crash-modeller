# Portfolio crash modeller

**How would your investments have coped with a crash?** Try out different ways to split your
money, see how each would have done in real crashes such as 2008 and 2020, then track the one you
choose.

> **Not investment advice.** This is a learning and portfolio project. Past performance, real or
> simulated, is not a reliable indicator of future results.

## The journey

1. **Design** a split: the index funds and ETFs you hold or are weighing up, in the proportions you
   have in mind.
2. **Stress-test** it through real historical crashes, side by side with other splits.
3. **Decide** on one and lock it in with a start date and an amount.
4. **Track** how it is doing against inflation, cash and the splits you did not choose.

## Status

Early build. You can design up to four splits from named index funds and ETFs, such as S&P 500,
MSCI World and FTSE All-World trackers and sterling money market funds, or start from four
examples, and stress-test them through the 2000-03 dot-com crash, the 2007-09 financial crisis and
the 2020 Covid crash, in pounds. Every fund is modelled from the index it tracks, rebuilt from
published research data, after the fund's own ongoing charge; no index values or fund prices are
used ([ADR 0005](docs/decisions/0005-real-funds-modelled.md)). Each split's story says what drove
its fall, how far the pound's moves against the dollar helped or hurt, and how it would have done
if left alone rather than rebalanced. Gilt funds, more markets, deciding and tracking come next:
see the [roadmap](docs/roadmap.md). A live demo link will appear here.

## How it is built

| Folder | What is there |
|---|---|
| [`src/crashmodel/engine/`](src/crashmodel/engine/) | The financial calculations, as pure, typed functions with no I/O: calendar months, currency conversion, cash and bond returns, rebuilding an index from portfolios grouped by company size, fund charges, rebalancing or leaving a split alone, worst fall and recovery, which holdings drove a fall, and the crash windows. Each is tested against hand-worked figures. |
| [`src/crashmodel/data/`](src/crashmodel/data/) | The open data stored with the app, the runtime fetch of share portfolios, the index models, the catalogue of funds and indexes, and every model's monthly returns in pounds. Sources and licences are in [DATA_LICENCES.md](DATA_LICENCES.md). |
| [`src/crashmodel/app/`](src/crashmodel/app/) | The Streamlit app. `stress.py` runs the visitor's splits through the engine; presenters turn the results into words and are unit tested; pages only lay them out. |
| [`docs/decisions/`](docs/decisions/) | Why the method and the data are as they are. |
| [`tools/`](tools/) | The build tool for the stored data, and the style, hygiene and privacy checks the hooks run. |

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
written, and refuses to run without a denylist. It reads only the words of `uv.lock` and the stored
monthly series, whose figures match amounts by chance, and skips the words of the fund names and
tickers in the fund list, which may also be on your denylist. It is a safety net, not a guarantee,
so still review what you commit.

## Licence

The code is released under the [MIT licence](LICENSE). Data has its own terms: see
[DATA_LICENCES.md](DATA_LICENCES.md).
