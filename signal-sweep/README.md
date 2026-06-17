# Signal Sweep

An [agent skill](SKILL.md) that surfaces new investment ideas for a long-only investor. It
scans SEC filings and market data across the $50M–$10B US-listed universe (NYSE, NASDAQ, OTC)
and produces actionable shortlists of tickers with reasons — the top of the funnel that feeds
[`bottom-up-analyst`](../bottom-up-analyst/).

## Where it sits

```
  signal-sweep  (this skill — produces tickers)
       │
       ▼
  bottom-up-analyst  (deep dive on one ticker)
       ├── sec-edgar-skill  (SEC filings)
       ├── market-scout     (price, peers, transcripts)
       ▼
  pitch-like-lou  (finished pitch)
```

The data skills (`sec-edgar-skill`, `market-scout`) research a company you already have in
mind. This skill answers the prior question: *which companies should you look at?*

## What it scans

| Capability | Script | Cadence |
|---|---|---|
| **Insider cluster buys + 13D alerts** | `scan_insiders.py` | Daily CI (cron) or on-demand |
| **Market screens** (7 presets, config-driven) | `scan_market.py` | On-demand |
| **Keyword / theme discovery** (EFTS full-text search) | `search_themes.py` | On-demand |
| **Conference discovery** (8-K Item 8.01) | `scan_conferences.py` | On-demand |

See [SKILL.md](SKILL.md) for invocation details and flags.

## Setup

1. **Install dependencies** (Python ≥ 3.10):
   ```bash
   pip install -r requirements.txt    # edgartools, yfinance, pandas, requests
   ```
2. **Set `EDGAR_IDENTITY`** — required for insider and theme scans (see
   [repo-level setup](../README.md#setup)).
3. Market screens (`scan_market.py`) use Yahoo Finance only and need no identity.

## Screen customization

Screen definitions live in [`screens.json`](screens.json). Edit the JSON to add, remove, or
tweak screens — no Python changes needed. See [`references/guide_screens.md`](references/guide_screens.md)
for the full yfinance field reference.

## Daily CI (GitHub Actions)

The insider scan is designed to run daily on a cron. The workflow at
`.github/workflows/insider-scan.yml` runs at 7 AM ET on weekdays, posts results to
Discord, and uploads the Markdown output as a build artifact (90-day retention).

**Required secrets:**
- `EDGAR_IDENTITY` — your SEC identity (see [repo-level setup](../README.md#setup))
- `DISCORD_WEBHOOK_URL` — (optional) Discord webhook for posting alerts

The workflow also supports `workflow_dispatch` for manual runs with custom date,
lookback, and z-score threshold inputs.

---
Part of the [us-market-research-skills](../README.md) stack.
