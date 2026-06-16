---
name: sec-edgar-skill
description: >-
  Retrieve and extract SEC EDGAR filings and ownership data for US-listed companies. Use this
  whenever a task touches a company's filings, financials, ownership, governance, or
  institutional holders — even if EDGAR is not named explicitly. Covers 10-K/10-Q/8-K,
  20-F/6-K foreign filings, XBRL financial statements, insider transactions, 13F institutional
  holdings (via 13f.info), 13D/13G blockholdings, and DEF 14A proxy/compensation. Always start
  by running scripts/orient.py, then pull only the sections you need. Unopinionated data layer:
  it fetches and extracts token-efficiently; it does not decide what is significant.
---

# SEC EDGAR Research Skill

A toolkit for retrieving and extracting SEC EDGAR filings for US-listed companies —
efficiently, within a token budget, using `edgartools`.

## What this skill is — and is not

This is the **tools layer** of a research stack. It knows *how* to find, download, and
extract SEC filing data, plus the library mechanics to do it reliably. It is
deliberately **unopinionated**: it does not judge what is a good number, a red flag, or
worth looking at. That judgment belongs to whatever **analytical-framework skill** is
driving (e.g. a value-investing framework); presentation belongs to a downstream
consumer skill. Keep this layer neutral so any framework can compose on top of it.

Provide capability and facts; let the caller reason. The only hard requirements here are
mechanical (set an SEC identity, or requests are blocked) — never analytical.

## Setup (once per environment)

1. **SEC identity — required.** The SEC blocks anonymous requests with HTTP 403. Set a
   real `Name email` once; every script reads it automatically:
   - PowerShell: `$env:EDGAR_IDENTITY = "Jane Analyst jane@example.com"`
   - Bash: `export EDGAR_IDENTITY="Jane Analyst jane@example.com"`

   (or pass `--identity "Name email@example.com"` to any script).
2. **Python ≥ 3.10** with the dependencies installed. Use that interpreter directly
   (e.g. `.venv\Scripts\python.exe` on Windows, `.venv/bin/python` elsewhere). Install
   with `pip install -r requirements.txt` (`edgartools` and `pandas` are required;
   `truststore` is optional, for inspecting corporate proxies).
3. **Verify:** `python scripts/test_setup.py --live` checks dependencies, identity, the
   cache location, and (with `--live`) makes one real SEC request.

The scripts handle environment hazards on import (UTF-8 stdout on Windows, truststore
for corporate proxies). When you run **inline Python** instead of a script, replicate
that preamble — see `references/guide_core.md` § "Inline Python preamble."

## How to work efficiently: pull only what you need

Filings are huge — a 10-K can exceed 100k words. Loading one whole wastes the context
window and buries the signal. The method is to keep documents **on disk** and pull only
the exact lines you need into context. Four phases:

1. **Orient first — always run `scripts/orient.py`.** `python scripts/orient.py --ticker <T>`
   prints the company's `.to_context()` summary, surveys the **mix of forms it has actually
   filed** (with date ranges), and lists the most recent filings — the cheapest way to see what
   a company files *now* and how that has changed, so you fetch the right forms instead of
   assuming a form set. This is the **non-negotiable first step — run it before any web
   search, even for breaking news.** When the user says "just reported" or "a few hours ago,"
   orient.py will show the 8-K filed today immediately; then fetch it with
   `fetch_filing.py --form 8-K --date <today> --attachment list` to get the press-release
   exhibit (Exhibit 99.1). The filing is always faster and more authoritative than a web
   search for what the company itself disclosed. (For finer control, `.to_context()`
   on a `Company`, filing collection, or `XBRL` object gives the same preview inline — see
   `guide_core.md`.)
2. **Download to the cache as Markdown.** Use the scripts to write filings to disk as
   clean Markdown — `edgartools` converts SEC HTML, stripping layout bloat to roughly a
   tenth of the size, and the result is greppable.
3. **Get just the section you need.** Item-addressable forms (10-K/10-Q/8-K/20-F) let you
   list a filing's SEC item codes and pull one section by code — no scanning. For a full
   report, `scripts/list_headings.py` maps its `#` headers to line numbers; tabular
   free-form filings (e.g. DEF 14A) instead carry their own table of contents up top —
   read it, then grep. `guide_filings.md` has the mechanics.
4. **Search, then read precisely.** Use your native grep/ripgrep over the cached files
   to find the lines that matter, then read just those ranges. Let grep and disk do the
   heavy lifting; spend context only on the paragraphs you actually need.

## The cache

Downloads go to `<cache>/<TICKER>/<FORM>_<FILING-DATE>_<ACCESSION>[__<section-or-exhibit>].md`
(statements as `…__<statement>.csv`). The root resolves as `--cache-dir` >
`$SEC_CACHE_DIR` > `./sec-cache` — workspace-relative so your grep tool finds it by
default, and persistent across runs so you don't re-hit the SEC. Filenames are
deterministic and keyed by the globally-unique accession number, so **before
downloading, check whether the file already exists** (list or glob `<cache>/<TICKER>/`)
and reuse it. Every script prints the absolute path(s) it wrote to stdout.

> If your grep tool uses ripgrep and the cache is gitignored, ripgrep skips it by
> default. Either point the search at `<cache>/<TICKER>/` explicitly, or pass
> `--no-ignore`. Resolve the path from a script's stdout or `$SEC_CACHE_DIR` — never
> hard-code an absolute cache path.

## Reference guides (read the relevant one before extracting)

Each guide is loaded only when its domain is in play, so you carry just the rules you
need. Read the matching guide first — it holds the item codes, taxonomies, and library
quirks that make extraction correct.

| Guide | Use it for |
| :-- | :-- |
| `references/guide_core.md` | The mechanics behind `scripts/orient.py`: resolving a company, listing/filtering filings, surveying the filing mix, `.to_context()` previews, and `.docs` self-help. Read it to drive orientation inline or go beyond the script. |
| `references/guide_filings.md` | Filing text: pulling a section by SEC item code (10-K/10-Q/8-K/20-F) vs. navigating free-form filings (DEF 14A/6-K) by their own contents, plus attachments and exhibits (incl. 6-K Exhibit 99.1). |
| `references/guide_financials.md` | XBRL financial statements and individual facts (US-GAAP and IFRS), and the period-aggregation pitfalls. |
| `references/guide_ownership.md` | Insider transactions (Forms 3/4/5), beneficial ownership, and executive compensation (DEF 14A; Form 20-F Item 6 for foreign issuers). |
| `references/guide_holdings.md` | **Deep route only:** raw 13F via edgartools (voting authority, amendments, specific holdings) and 5%+ blockholders (13D/13G). For the common case — “who owns this stock?” — use `scripts/fetch_13f_holders.py` directly (see Scripts above); no guide needed. |

## Scripts

Run them with the project's Python. Each prints the absolute cache path(s) it wrote to
stdout and logs progress to stderr. **`--help` is the authoritative flag reference** —
the list below shows one canonical invocation each:

```bash
# Orient first: company summary + filing-mix survey + recent filings
python scripts/orient.py --ticker AAPL

# One filing (full), a single section, or an attachment — into the cache
python scripts/fetch_filing.py --ticker AAPL --form 10-K --year 2023
python scripts/fetch_filing.py --ticker AAPL --form 10-K --year 2023 --section "Item 1A"  # or: --section list
python scripts/fetch_filing.py --ticker WIX  --form 6-K  --attachment "ex-99.1"   # or: list | all | <index>

# Target a filing by date (e.g. an 8-K filed today) instead of just --year:
python scripts/fetch_filing.py --ticker AAPL --form 8-K --date 2026-06-15

# Many filings across a year range (add --attachments to capture e.g. 6-K exhibits)
python scripts/fetch_filings.py --ticker AAPL --form 10-Q --start-year 2022 --end-year 2024

# XBRL statements (income | balance | cashflow | all) -> CSV (annual or quarterly)
python scripts/parse_financials.py --ticker AAPL --year 2023 --statement all
python scripts/parse_financials.py --ticker AAPL --year 2024 --quarter 1 --statement all

# Table of contents for a large cached filing
python scripts/list_headings.py --file sec-cache/AAPL/10-K_2023-11-03_0000320193-23-000106.md

# 13F institutional holders — who owns this stock? (via 13f.info, no SEC identity needed)
python scripts/fetch_13f_holders.py --ticker AAPL --top 15

# 13F holder history — how has institutional ownership changed?
python scripts/fetch_13f_holders.py --ticker AAPL --history

# 13F manager search — what does a specific fund hold?
python scripts/fetch_13f_holders.py --manager "Berkshire Hathaway"

# 13F cross-reference — one manager's position history in one stock
python scripts/fetch_13f_holders.py --cik 0000906304 --cusip 205826209

# Environment diagnostics
python scripts/test_setup.py --live
```

## When the API surprises you: self-heal with `.docs`

`edgartools` documents itself at runtime. If a method or attribute isn't what you
expected, query it inline instead of guessing — this recovers from most API uncertainty
without leaving the session:

```python
company.docs                 # full API guide for the object
company.docs.search("xbrl")  # search it for a topic
```

A tool error is almost always a fixable usage detail, not a dead end. When a script or call
fails, **recover here** — re-run `scripts/orient.py`, query `.docs`, or read the relevant
guide — rather than abandoning EDGAR for web search. The filings are the authoritative,
auditable source; don't let a transient error push the work onto unverifiable web results.

**Amendment vs. original filing.** `fetch_filing.py` always skips amended forms
(10-K/A, 10-Q/A, etc.) and picks the most recent *original* filing. Amendments typically
contain only the amended items (e.g. Part III), not the full filing, so silently picking
one would lose most of the content. If you specifically need an amendment's items, fetch
it by accession number using inline Python as shown in `guide_financials.md`.
