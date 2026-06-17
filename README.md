# US Market Research Skills

A composable stack of [agent skills](https://www.skills.sh/) for rigorous bottom-up equity
research on US-listed companies — from idea discovery through primary data (SEC filings +
market data), through an analytical framework, to a finished pitch. Each skill stands on its
own; together they form a pipeline.

## The skills

| Layer | Skill | Job |
|---|---|---|
| **Discovery** | [`signal-sweep`](signal-sweep/) | Scan SEC filings and market data across the $50M–$10B universe to surface new investment ideas: insider cluster buys, market screens, keyword/theme search, conference discovery. |
| **Data** | [`sec-edgar-skill`](sec-edgar-skill/) | Retrieve & extract SEC EDGAR filings (10-K/10-Q/8-K, 20-F/6-K, XBRL financials, ownership, holdings) and 13F institutional holder data (via 13f.info), token-efficiently. Unopinionated. |
| **Data** | [`market-scout`](market-scout/) | Pull price, returns, peers, sector screens, and earnings call transcripts via Yahoo Finance. Unopinionated. |
| **Analysis** | [`bottom-up-analyst`](bottom-up-analyst/) | Turn one ticker into an earned, auditable investment memo — drives the data skills, classifies the archetype, values it, tries to kill it. |
| **Voice** | [`pitch-like-lou`](pitch-like-lou/) | Render a Norbert Lou–style Value Investors Club pitch from a finished thesis. |

## How they compose

```
  signal-sweep  (surfaces tickers)
       │
       ▼
  bottom-up-analyst  (deep dive on one ticker)
       ├── sec-edgar-skill  (SEC filings)
       ├── market-scout     (price, peers, transcripts)
       ▼
  pitch-like-lou  (finished pitch)
```

- **Discovery feeds analysis.** `signal-sweep` scans the universe and produces shortlists of
  tickers with reasons. `bottom-up-analyst` takes one of those tickers and does the deep dive.
  They are independent — you can skip discovery and hand the analyst a ticker directly.
- **The two data skills are independent and swappable.** `sec-edgar-skill` (filings) and
  `market-scout` (market data) know nothing of each other; either can be replaced — e.g. point
  the analyst at a paid data provider instead of `market-scout` and nothing else changes.
- **The analyst is the brain and the conductor.** `bottom-up-analyst` decides what to pull,
  reasons over it, values the business, and writes the memo. It drives the data skills; they
  never decide what matters.
- **The voice renders from a finished thesis.** `pitch-like-lou` turns the analyst's memo into a
  pitch; it is not an idea generator.

**Production order:** signal-sweep → analyst → memo → (optionally) Lou pitches from it.

## Install

Install the whole stack, or any single skill on its own, with [skills.sh](https://www.skills.sh/)
— point it at this repository, or at a single skill subfolder. Each skill is a self-contained
folder with its own `SKILL.md`.

## Setup

### SEC identity (required)

The SEC's [fair-access policy](https://www.sec.gov/os/webmaster-faq#developers) requires a
contact name and email in the User-Agent header. Requests without one are blocked (HTTP 403).
Set it once — `sec-edgar-skill` and `signal-sweep` both read it automatically:

```bash
export EDGAR_IDENTITY="Jane Analyst jane@example.com"     # bash/zsh
$env:EDGAR_IDENTITY = "Jane Analyst jane@example.com"     # PowerShell
```

Use your real name and email. The SEC uses this only to contact you if your traffic causes
problems — it is not authentication.

### Per-skill dependencies

- **`signal-sweep`** — `pip install -r signal-sweep/requirements.txt`
- **`sec-edgar-skill`** — `pip install -r sec-edgar-skill/requirements.txt`
- **`market-scout`** — `pip install -r market-scout/requirements.txt`. No identity needed.
  For earnings call transcripts: `npm install -g dev-browser && dev-browser install`.
- **`bottom-up-analyst`** — valuation scripts are standard-library only; no install needed.
- **`pitch-like-lou`** — documentation and a reference corpus; nothing to install.

## A note on scope

These skills produce **research, not advice**. They are tools for doing diligence rigorously and
honestly; nothing they output is a recommendation to buy or sell a security. The whole design —
filings-first grounding, verified-vs-assumed tagging, the pre-mortem — exists to keep an LLM's
fluent prose tethered to auditable evidence so a human can reach their own judgment.
