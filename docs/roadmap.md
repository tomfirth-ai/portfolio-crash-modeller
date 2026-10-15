# Roadmap

The tool is built in vertical slices. Each slice ends with something a visitor can use on the live app,
and is tried by the owner there before the next one starts. The reasons are in
[ADR 0004](decisions/0004-vertical-slices.md).

| Slice | A visitor can... | Status |
|---|---|---|
| **1a. See it** | see four example splits through the 2007-09 financial crisis and the 2020 Covid crash, in pounds, with real data: a card in words for each split, a table and a chart | done |
| **1b. Make it yours** | edit up to four splits, from a template or their own numbers, and stress-test them | done |
| **2. Deeper stress-test** | see why each split fell as it did: what the pound did to overseas shares, which holdings drove the fall, rebalanced against left alone, what each split holds, and a third crash, the 2000-03 dot-com crash | in progress |
| **3. Decide and track** | lock in one split with a start date and an amount, then follow it month by month against inflation, cash and the splits not chosen | planned |
| **4. Public launch** | read how every figure is worked out, and find the project on GitHub | planned |

Later: a rules engine for staged buying in a fall, a local mode that tracks a real portfolio kept
outside the repository, and an optional assistant that explains the results in words.
