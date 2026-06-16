---
name: market-scout
description: >-
  Pull public market data for US-listed stocks via Yahoo Finance (yfinance): current price,
  market cap, shares, 52-week range, trailing returns, sector/industry peer tables, pre-ranked
  screens (top by weight, top performers, top growth), and earnings call transcripts. Use this
  whenever a task needs a quick market snapshot or quote for a ticker, trailing performance, a
  company's peer set, a sector/theme shortlist, or earnings call transcripts — e.g. "what's
  the price/return on X", "who are X's peers", "best-performing names in this industry",
  "get me the latest earnings call", or turning a theme into a concrete list of tickers to
  investigate. This is an unopinionated market-data layer: it surfaces facts and rankings;
  it does not decide what is cheap, good, or worth buying.
---

# Market Scout

Pull **public market data** and do light **sector/peer screening** for US-listed stocks with
`yfinance`, plus **earnings call transcripts** from Yahoo Finance (via `dev-browser`).
Unopinionated: it surfaces prices, returns, peers, rankings, and management commentary; it
does not decide what is cheap or worth buying — leave that to whatever framework is driving.

## Setup

Install the deps (Python ≥ 3.10); **no API key or identity is needed** — Yahoo Finance is public.

```bash
pip install -r requirements.txt    # yfinance + pandas
```

For earnings call transcripts, `dev-browser` must also be installed:

```bash
npm install -g dev-browser && dev-browser install
```

## yfinance is self-documenting — discover, then construct

The bundled script wraps only the common snapshot/returns/peers case. yfinance exposes far more
(financials, holders, options, earnings dates, calendar, sector/industry screens, …). **Do not
assume or hard-code field names — discover them at runtime** and build exactly what the task
needs:

```python
import yfinance as yf
t = yf.Ticker("AAPL")

print([a for a in dir(t) if not a.startswith("_")])   # all attributes/methods
help(yf.Ticker)                                         # full documented API
list(t.info.keys())                                     # every field in the snapshot

# Sector/industry screening primitives (great for a theme -> shortlist):
ind = yf.Industry(t.info["industryKey"])
print([a for a in dir(ind) if not a.startswith("_")])  # top_companies,
                                                        # top_performing_companies,
                                                        # top_growth_companies, overview, ...
```

When a field or method isn't what you expected, `dir()` / `help()` / `.info.keys()` recover the
answer inline — prefer that over guessing.

> **Note:** yfinance does **not** provide earnings call transcripts. Those are fetched
> separately by `fetch_transcripts.py` using `dev-browser` to scrape Yahoo Finance's
> Quartr-powered transcript pages.

## Scripts

Run with the project's Python. `--help` is the authoritative flag reference:

```bash
# Market snapshot + trailing returns + industry peers
python scripts/fetch_market_data.py --ticker AAPL --industry --peers

# Earnings call transcripts — list what's available
python scripts/fetch_transcripts.py --ticker AAPL --list

# Download the latest transcript
python scripts/fetch_transcripts.py --ticker AAPL --latest 1

# Download all transcripts for a specific fiscal year
python scripts/fetch_transcripts.py --ticker AAPL --year 2025

# Download a specific quarter
python scripts/fetch_transcripts.py --ticker AAPL --quarter Q3 --year 2025

# Download all available transcripts
python scripts/fetch_transcripts.py --ticker AAPL
```

### Transcript cache

Transcripts are saved as LLM-friendly Markdown to `transcript-cache/<TICKER>/transcripts/`
(override with `--cache-dir` or `$TRANSCRIPT_CACHE_DIR`). Files are named `Q3-FY2026.md`
etc., cached and reused across runs. Each file has a summary, `## Prepared Remarks` with
`### Speaker — Title` headings, and a `## Q&A` section — greppable by speaker name,
"guidance", "margin", or any keyword.
