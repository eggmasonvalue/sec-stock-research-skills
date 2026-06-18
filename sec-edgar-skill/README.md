# SEC EDGAR Research Skill

A tools skill that teaches an AI coding agent how to retrieve and extract data from
**SEC EDGAR** filings for US-listed companies (domestic issuers and foreign private
issuers), efficiently and within a token budget.

It is the **data/tools layer** of a research stack: it fetches and extracts; it does not
decide what matters. Pair it with an analytical-framework skill (which supplies the
judgment and the output shape) and, optionally, a presentation/consumer skill. Keeping
this layer unopinionated lets any framework compose on top of it.

## What's included

- **`SKILL.md`** — the entry point: setup, the token-efficient retrieval method, the
  cache contract, and routing to the guides and scripts.
- **`references/`** — modular, lazily-loaded guides, one per data domain:
  - `guide_core.md` — company lookup, filing discovery, `.to_context()`, `.docs`.
  - `guide_filings.md` — filing text by SEC item code (10-K/10-Q/8-K/20-F) or heading discovery (DEF 14A/6-K); attachments (6-K Exhibit 99.1).
  - `guide_financials.md` — XBRL statements and facts (US-GAAP & IFRS).
  - `guide_ownership.md` — insider transactions (3/4/5) and executive compensation (DEF 14A; 20-F Item 6).
  - `guide_holdings.md` — 13F institutional holdings and 13D/13G blockholders.
- **`scripts/`** — thin, self-documenting wrappers around `edgartools` (shared setup
  lives in `_common.py`):
  - `orient.py` — company summary + filing-mix survey + recent filings (run first).
  - `fetch_filing.py`, `fetch_filings.py` — filings (and sections/attachments) to Markdown.
  - `parse_financials.py` — XBRL statements to CSV.
  - `list_headings.py` — heading→line map for a cached filing.
  - `fetch_insider_trades.py` — insider transactions (Form 4 buys/sells).
  - `fetch_13f_holders.py` — institutional 13F holders (via 13f.info).
  - `test_setup.py` — environment diagnostics.

## Setup

1. **Install dependencies** (Python ≥ 3.10): `pip install -r requirements.txt`
2. **Set `EDGAR_IDENTITY`** — see [repo-level setup](../README.md#setup).
3. **Verify:** `python scripts/test_setup.py --live`

## Add the skill to your agent

```bash
npx skills add eggmasonvalue/sec-edgar-skill
```

## How it works

Filings are huge, so the skill keeps them on disk and pulls only what's needed into the
agent's context:

1. **Orient** with `scripts/orient.py` (company summary + filing-mix survey) to decide what to fetch.
2. **Download** filings to a local cache (`./sec-cache/{TICKER}/`) as clean Markdown.
3. **Map** a large filing to a heading→line table of contents.
4. **Search** the cache with native grep and read only the matching line ranges.

The cache location is configurable (`$SEC_CACHE_DIR` or `--cache-dir`) and filenames are
deterministic (keyed by SEC accession number), so re-runs reuse cached files instead of
re-downloading.

## Data sources

Filing data comes from the public SEC EDGAR system via the open-source `edgartools`
library. Respect the source's terms and the SEC fair-access policy — which is why a
contact identity is required.

---
Part of the [us-market-research-skills](../README.md) stack.
