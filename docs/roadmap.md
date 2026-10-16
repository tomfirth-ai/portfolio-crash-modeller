# Roadmap

The tool is built in vertical slices. Each slice ends with something a visitor can use on the live app,
and is tried by the owner there before the next one starts. The reasons are in
[ADR 0004](decisions/0004-vertical-slices.md).

| Slice | A visitor can... | Status |
|---|---|---|
| **1a. See it** | see four example splits through the 2007-09 financial crisis and the 2020 Covid crash, in pounds, with real data: a card in words for each split, a table and a chart | done |
| **1b. Make it yours** | edit up to four splits, from a template or their own numbers, and stress-test them | done |
| **2. Deeper stress-test** | see why each split fell as it did: what the pound did to overseas shares, which holdings drove the fall, rebalanced against left alone, what each split holds, and a third crash, the 2000-03 dot-com crash | built, to be tried |
| **3. Real funds: shares and cash** | build splits from named S&P 500, MSCI World, FTSE All-World and FTSE Global All Cap trackers and sterling money market funds, each modelled from open data after its charges ([ADR 0005](decisions/0005-real-funds-modelled.md)) | built, to be tried |
| **4. Real funds: gilts and 2022** | add all-maturity, short and long gilt funds, modelled from the Bank of England's gilt yield curve, and see the 2022 bond crash | planned |
| **5. Real funds: more markets** | add FTSE All-Share, FTSE 100, Nasdaq-100, Europe ex UK, Japan and emerging markets trackers | planned |
| **6. Real funds: linkers and global bonds** | add index-linked gilt funds, US Treasury funds and global bond funds hedged to the pound | planned |
| **7. Decide and track** | lock in one split with a start date and an amount, then follow it month by month against inflation, cash and the splits not chosen | planned |
| **8. Public launch** | read how every figure is worked out, and find the project on GitHub | planned |

Later: a local mode that runs on the owner's machine with real fund and index data, multi-asset funds
modelled as blends, corporate bonds and gold, the 1987 crash, a rules engine for staged buying in a
fall, and an optional assistant that explains the results in words.
