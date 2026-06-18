---
name: signal-sweep
description: >-
  Surface new investment ideas for a long-only investor by scanning SEC filings and market
  data across the $50M–$10B US-listed universe. Use this skill whenever the user wants to
  discover new tickers — not research a specific one they already have. Triggers include
  "what should I look at", "show me insider buying", "any cluster buys", "what's near its
  52-week low", "run the screens", "who's exposed to [theme]", "which companies mention
  [keyword] in filings", "who's presenting at conferences this week", "find me new ideas",
  "surface some names", "what's interesting in small caps", or any request to scan, screen,
  or sweep for investment candidates. Do NOT use this for single-company deep dives (that's
  bottom-up-analyst), individual stock quotes (market-scout), or pulling a specific filing
  (sec-edgar-skill). This skill produces tickers; the rest of the stack researches them.
---

# Signal Sweep

Top-of-funnel idea surfacing for long-only investors. Scans SEC filings and market data
across a configurable US-listed universe (NYSE, NASDAQ, OTC) and produces shortlists of
tickers with reasons. It sits upstream of the research stack — it *produces* tickers that
`bottom-up-analyst` then deep-dives. The market-cap floor and ceiling are set in
`screens.json` under `universe.market_cap_min` / `universe.market_cap_max` (default
$50M–$10B); all scripts read from that file.

## Capabilities

### 1. Insider buying scanner + 13D alerts

Scans Form 4 open-market purchases (code `P` only) and detects three signal types:

- **Cluster buys:** 2+ distinct insiders buying the same stock within the lookback
  window. Breadth signal — multiple people agree.
- **Dip buys:** an insider buys after an unusually large decline, measured against the
  stock's own volatility (trailing 30-day return z-score ≤ -1.5σ). A CEO buying into a
  -2σ drawdown on a normally calm stock is high-signal even without a second insider.
- **Rip buys:** an insider buys after an unusually large rally (z-score ≥ +1.5σ).
  Insiders usually buy on weakness — buying into strength suggests the move has legs.

The z-score is volatility-adjusted: a 20% drop is routine for a biotech but exceptional
for a utility. The threshold adapts to each stock's personality.

```bash
# On-demand
python scripts/scan_insiders.py --date yesterday --lookback 5

# Tighter threshold (only flag ≥2σ moves)
python scripts/scan_insiders.py --date yesterday --lookback 5 --zscore 2.0

# Daily CI with Discord webhook
python scripts/scan_insiders.py --date yesterday --lookback 5 --webhook $DISCORD_WEBHOOK_URL
```

Option exercises, tax withholding, awards, gifts, and sales are filtered out.
`--help` for all flags.

### 2. Market screens

Config-driven screens via yfinance. Definitions live in `screens.json` — edit the JSON
to add or tweak screens, no Python changes needed.

```bash
python scripts/scan_market.py --screen near-52wk-low
python scripts/scan_market.py --all
python scripts/scan_market.py --list
```

The 7 presets: `near-52wk-low`, `high-short-interest`, `short-covering`, `insider-heavy`,
`fallen-from-grace`, `low-institutional`, `forgotten`. Each enriches the top results with
P/E, short %, insider %, analyst rating, and sector. `--no-enrich` for
faster runs. See `references/guide_screens.md` for the field reference and how to add
custom screens.

### 3. Keyword / theme discovery

Goes from a keyword to a list of exposed companies by searching the full text of SEC
filings via EDGAR's EFTS engine. Finds non-obvious exposures — the REIT that leases to
cannabis growers, the testing lab, the BDC that lends to the sector.

```bash
python scripts/search_themes.py --keyword "cannabis" --since 2026-01-01
python scripts/search_themes.py --keyword "tariff" --since 2025-01-01 --until 2026-06-17
```

Results are deduplicated by company, filtered to the configured universe, and enriched.

### 4. Conference discovery

Finds companies presenting at conferences by scanning 8-K Item 8.01 filings for
conference-related keywords.

```bash
python scripts/scan_conferences.py --start 2026-06-16 --end 2026-06-20
```

Item 8.01 is a catch-all, so expect some false positives. The interesting follow-ups are
interactive — "which of these also show insider buying?", "any in healthcare?"

## Output

Every script writes a timestamped `.md` to `signal-sweep-cache/` and prints the absolute
path to stdout (same `emit(path)` pattern as `sec-edgar-skill`). Market-cap lookups are
cached to disk with a 24h TTL.

## Resources

| File | Purpose |
|------|---------|
| `screens.json` | The 7 preset screen definitions (user-editable) |
| `references/guide_screens.md` | yfinance EquityQuery field reference + custom screen howto |
