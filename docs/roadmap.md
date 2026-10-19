# Roadmap

The tool is built in vertical slices. Each ends with something a visitor can use on the live app, and
is tried by the owner there before the next one starts. The reasons are in
[ADR 0004](decisions/0004-vertical-slices.md).

After Slice 4 the app goes public as release v0.1. Each later release is built on a branch, reviewed
in one pull request and published with a release note, so the project grows in the open.

## Built before the first release

| Slice | A visitor can... | Status |
|---|---|---|
| **1a. See it** | see four example splits through the 2007-09 financial crisis and the 2020 Covid crash, in pounds, with real data: a card in words for each split, a table and a chart | done |
| **1b. Make it yours** | edit up to four splits, from a template or their own numbers, and stress-test them | done |
| **2. Deeper stress-test** | see why each split fell as it did: what the pound did to overseas shares, which holdings drove the fall, rebalanced against left alone, what each split holds, and a third crash, the 2000-03 dot-com crash | done |
| **3. Real funds: shares and cash** | build splits from named S&P 500, MSCI World, FTSE All-World and FTSE Global All Cap trackers and sterling cash ETFs that track SONIA, each modelled from open data after its charges ([ADR 0005](decisions/0005-real-funds-modelled.md)) | done |
| **4. Real funds: gilts and 2022** | add all-maturity, short and long gilt funds, modelled from the Bank of England's gilt yield curve, with cash on SONIA, and see the 2022-23 bond crash ([ADR 0006](decisions/0006-gilts-and-sonia.md)) | built, to be tried |

## Releases

| Release | A visitor can... | Status |
|---|---|---|
| **v0.1 Launch** | use Design and Stress-test in public, read how every figure is worked out, and find the code on GitHub | in progress |
| **v0.2 Decide and Track** | lock in one split with a start date and an amount, then follow it month by month against inflation, cash and the splits not chosen; splits survive a reload and can be shared by link | planned |
| **v0.3 Explained** | ask for each split's result to be explained in plain words | planned |
| **v0.4 More markets** | add FTSE All-Share, FTSE 100, Nasdaq-100, Europe ex UK, Japan and emerging markets trackers | planned |
| **v0.5 Linkers and global bonds** | add index-linked gilt funds, US Treasury funds and global bond funds hedged to the pound, with gilt funds that follow Bloomberg's maturity rules | planned |

Later: a rules engine for staged buying in a fall, real closing prices of the chosen ETFs on the Track
page, a local mode that runs on the owner's machine with real fund and index data, multi-asset funds
modelled as blends, corporate bonds and gold, and the 1987 crash.
