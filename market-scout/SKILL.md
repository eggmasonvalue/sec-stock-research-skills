---
name: market-scout
description: >-
  Pull public market data for US-listed stocks via Yahoo Finance: price, market cap, shares,
  52-week range, trailing returns, sector/industry peer tables and pre-ranked screens, and
  earnings call transcripts. Use this whenever a task needs a quick market snapshot or quote
  for a ticker, trailing performance, a company's peer set, a sector/theme shortlist, or
  earnings call transcripts — e.g. "what's the price/return on X", "who are X's peers",
  "best-performing names in this industry", "get me the latest earnings call", or turning a
  theme into a concrete list of tickers. This is an unopinionated data layer; it does not
  decide what is cheap, good, or worth buying.
---

# Market Scout

Pull **public market data**, **sector/peer screening**, and **earnings call transcripts**
for US-listed stocks. Unopinionated: it surfaces prices, returns, peers, rankings, and
management commentary; it does not decide what is cheap or worth buying — leave that to
whatever framework is driving.

## Setup

```bash
pip install -r requirements.txt    # yfinance + pandas (Python ≥ 3.10)
```

For earnings call transcripts, `dev-browser` must also be installed:

```bash
npm install -g dev-browser && dev-browser install
```

No API key or identity is needed — Yahoo Finance is public.

## Market snapshot and peers

`fetch_market_data.py` prints a compact Markdown summary to stdout — price, market cap,
shares outstanding, 52-week range, trailing returns, and (optionally) industry overview and
peer tables. Output is live and never cached. `--help` is the authoritative flag reference:

```bash
python scripts/fetch_market_data.py --ticker AAPL --industry --peers
```

## Earnings call transcripts

`fetch_transcripts.py` scrapes Yahoo Finance's Quartr-powered transcript pages via
`dev-browser` (Yahoo requires JS rendering). It lists available transcripts or downloads
them as LLM-friendly Markdown to `transcript-cache/<TICKER>/transcripts/`. Files are
named `Q3-FY2026.md` etc., cached and reused across runs. `--help` for all flags:

```bash
python scripts/fetch_transcripts.py --ticker AAPL --list           # list available
python scripts/fetch_transcripts.py --ticker AAPL --latest 1       # most recent
python scripts/fetch_transcripts.py --ticker AAPL --year 2025      # full fiscal year
python scripts/fetch_transcripts.py --ticker AAPL --quarter Q3 --year 2025
```

Each cached file has a summary, `## Prepared Remarks` with `### Speaker — Title` headings,
and a `## Q&A` section — greppable by speaker name, "guidance", "margin", or any keyword.

## Beyond the bundled scripts — yfinance is self-documenting

The scripts above wrap the common cases. yfinance exposes far more (financials, holders,
options, earnings dates, calendar, sector/industry screens, …). When a task needs something
the scripts don't cover, **discover at runtime** rather than guessing field names:

```python
import yfinance as yf
t = yf.Ticker("AAPL")

print([a for a in dir(t) if not a.startswith("_")])   # all attributes/methods
list(t.info.keys())                                     # every field in the snapshot

# Sector/industry screening (theme -> shortlist):
ind = yf.Industry(t.info["industryKey"])
print([a for a in dir(ind) if not a.startswith("_")])  # top_companies, overview, ...
```

When a field or method isn't what you expected, `dir()` / `help()` / `.info.keys()` recover
the answer inline — prefer that over guessing.
