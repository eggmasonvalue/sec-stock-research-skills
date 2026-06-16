---
name: bottom-up-analyst
description: >-
  Run a rigorous bottom-up fundamental deep dive on a single company and produce a
  pitch-ready investment memo. Use this skill whenever the user hands you one stock — a
  ticker or a name — and wants real due diligence: an investment thesis, a long/short
  case, "is this a buy?", a valuation, a bull/bear teardown, an earnings-quality check, or
  a full research write-up. It is the analytical engine of a research stack: it drives
  SEC-filing and market-data tools for grounding, reasons over the evidence to an *earned*
  conviction, classifies the company into an archetype (compounder, hypergrowth, cyclical,
  turnaround/inflection, special-situation, deep-value), triangulates an intrinsic-value
  range, tries to kill its own thesis, and writes the memo. Reach for it any time the task
  is "research this company" or "should I own this," even if neither "memo" nor "valuation"
  is said out loud.
---

# Bottom-Up Analyst

This skill is the **analyst** in a three-layer research stack. It turns *one name* into an
*earned thesis*, written up as a detailed, auditable investment memo that a reader can act
on. It does the work that sits between raw data and a finished pitch — the work of actually
deciding what the numbers mean.

## Where this sits — the seam with the other two skills

A bottom-up stack has three jobs, and they are deliberately kept separate:

- **The hands** — `sec-edgar-skill` (SEC filings and 13F institutional holder data) and
  `market-scout` (price, returns, the peer set, and earnings call transcripts):
  unopinionated data/tools layers. They fetch and extract token-efficiently; they *never*
  decide what matters.
- **The analyst — this skill.** It is both **the brain and the conductor.** It decides
  *what* to pull and *why*, reasons over it, values the business, stress-tests the
  conclusion, and writes the memo. The agent that chooses the evidence and the agent that
  judges it are the same agent — that is how real analysts work, and why this layer drives
  the tools rather than waiting to be handed numbers.
- **The voice** — `pitch-like-lou`: renders a *pitch* from a finished thesis. Short,
  compelling, "a pitch with conditions." A reader hooked by the pitch drops into **this
  skill's memo** for the full due diligence behind it.

So the production order is: **analyst → memo → (optionally) Lou pitches from it.** You
produce the substance. You do not need to invoke the voice skill yourself; your job is to
make the memo *pitch-ready* — complete and honest enough that a pitch can stand on it
without inventing anything.

## The prime directive: conviction must be earned, never manufactured

Every conclusion in the memo must trace to something you actually verified in a document
or computed yourself. This is not a style note — it is the whole point. A confident memo
built on an unchecked assumption is worse than no memo, because it *launders a guess into a
recommendation*. The discipline that prevents this is borrowed from the `pitch-like-lou`
corpus, and it is a **necessary condition on every memo regardless of company type**:

- **Separate what you *know* from what you *believe*.** State which claims are verified
  (with the source) and which are estimates or assumptions. Mark them differently in the
  memo so a reader can audit your confidence.
- **Concede the weak points out loud.** The bear case is part of *your* job, not the
  reader's. A thesis you have not tried to kill is not yet a thesis.
- **Tag second-hand claims as second-hand.** The cautionary tale from the corpus: a
  brilliant structural thesis (MCI QUIPS) nearly blew up because its author relayed
  *third-hand* that the books were clean; ~$24B of intercompany claims surfaced later. Know
  which claims you checked yourself, and flag the ones you didn't.
- **Demand a margin of safety.** Price the bad parts in — bad governance, dilution, cyclical
  risk — and require that the thesis survives anyway.

Lou's discipline is *necessary but not sufficient.* It is the quality gate every memo passes
through. It does **not** dictate the analysis — this skill researches companies Lou never
touched (hypergrowth tech, regulatory-tailwind inflections, turnarounds). The *method* below
supplies the sufficiency; Lou's temperament supplies the honesty.

## The loop

Work through these phases in order, but let the **archetype** decide where the weight goes —
a hypergrowth name lives in phases 3 and 6; a cyclical in 4; a special-situation in 5 and 7.
Do not pad a phase just because it exists.

1. **Orient and scope — filings first, always, before any web search.** Run
   `sec-edgar-skill`'s `scripts/orient.py` as the **very first tool call** — before web
   search, before `market-scout`, before anything else. This is non-negotiable even when the
   user describes breaking news ("just reported," "a few hours ago," "announced today").
   orient.py takes seconds and immediately shows you what was filed today; a web search for
   the same information is slower, less authoritative, and often wrong about the company.

   **Breaking-news pattern:** if the user mentions a same-day event, orient.py will show the
   8-K filed today. Immediately follow with:
   ```bash
   python scripts/fetch_filing.py --ticker <T> --form 8-K --date <today>
   python scripts/fetch_filing.py --ticker <T> --form 8-K --date <today> --attachment list
   # then fetch Exhibit 99.1 (the press release):
   python scripts/fetch_filing.py --ticker <T> --form 8-K --date <today> --attachment "ex-99.1"
   ```
   The press-release exhibit is the primary source; do not web-search for what it contains.

   After orient, read the latest **annual report** (10-K, or 20-F for an FPI) — its business
   section and MD&A — and skim the most recent **interim/current** reports (10-Q/8-K, or 6-K
   for an FPI) to learn, in the company's own words, *how it makes money.* You cannot value a
   business you cannot explain in one plain sentence. Pull the market snapshot (price, market
   cap, **the peer set**, sector) from `market-scout` to frame size and comps — orientation,
   not evidence.

   **Pull the latest earnings call transcript.** After the filing read and market snapshot,
   fetch the most recent earnings call transcript. This is a `market-scout` script (resolve
   the path against the `market-scout` skill directory, not this one):
   ```bash
   python scripts/fetch_transcripts.py --ticker <T> --latest 1
   ```
   Then read it (or grep it). The transcript is a **primary source** — management's own
   words on the quarter, forward guidance, strategic priorities, and tone — and it surfaces
   qualitative signals that filings alone do not convey: how management frames the
   competitive landscape, what questions analysts are pressing on, where the CEO hedges or
   deflects. The Q&A section is especially valuable: analyst questions often target exactly
   the weak points you need to stress-test in phase 6. Do not substitute a web summary of
   the call for the transcript itself — the summary loses the nuance that matters.

2. **Classify the archetype.** Almost every company is dominated by one shape, and the
   shape decides which DD emphases, metrics, disqualifiers, and valuation method carry the
   weight. Pick one primary archetype (a secondary is fine) and **load that playbook** from
   `references/archetypes/`. See the routing table below. When nothing fits cleanly, the
   core spine here is the fallback — reason from first principles.

3. **Reconstruct the normalized economics.** GAAP rarely shows the real earning power.
   Drive `sec-edgar-skill` to pull the statements (XBRL → CSV), then *un-distort* them:
   separate maintenance from growth capex, pull deferred revenue back into the picture, undo
   one-offs, treat stock-comp and leases honestly, build owner earnings / FCF. Show capital
   allocation as a **year-by-year table** (share count, debt, reinvestment, returns on it) —
   a trend persuades where a single number cannot. See `references/guide_normalization.md`.

   **When the thesis depends on a new revenue stream** — a pre-revenue JV, a partnership
   product, a market entry unlocked by regulation, a post-restructuring margin profile —
   build a **unit-economics bridge** from per-unit inputs (price, cost, volume) to the
   stream’s FCF contribution. A management TAM estimate plugged into a DCF growth rate is
   not a model; it launders a guess into a valuation. The bridge makes the assumption
   auditable: a reader who disagrees with your per-unit fee or customer count can re-run
   the math. See `references/guide_normalization.md` § “When the thesis depends on a new
   revenue stream.”

4. **Read the competitive and industry position.** A number is only as good as the moat
   under it. Establish industry structure, the company's place in it, and — the hard part —
   *relative* competitive advantage. **SEC filings are the default and the grounding**: the
   10-K's competition and risk-factor sections, and crucially the **peers' own filings**
   (their 8-Ks, 10-Qs, 10-Ks) for management commentary, pricing, and sentiment you can
   cite. **Peers' earnings call transcripts** are equally valuable primary sources — a
   competitor's CEO discussing pricing pressure, capacity additions, or market-share wins
   on their own call is citable competitive intelligence (`market-scout` script):
   ```bash
   python scripts/fetch_transcripts.py --ticker <PEER> --latest 1
   ```
   Then grep the cached transcript for the subject company's name, the product category,
   or pricing language. Use **web research only for what filings and transcripts genuinely
   cannot give you** — relative positioning, market-share dynamics, channel/customer
   checks — and label every web claim as such. See `references/guide_competitive.md`.

   **Quantify impact, don’t just list forces.** The most common failure in competitive
   analysis is cataloguing without sizing. For every moat mechanism, competitive threat,
   or risk factor, answer: *how big is it, how fast is it moving, and what is the dollar
   impact on this company if it plays out?* “High switching costs” is a label; “3-year
   migration timelines and 95%+ renewal rates” is evidence. “Competition is intensifying”
   is mood; “Competitor X grew Y% and holds Z% of the addressable market” is a fact the
   reader can reason from. A force you can’t size is one you haven’t understood — flag
   it [A] and name the gap. This discipline carries into the risks section (phase 6):
   every risk must pass a “so what” test with a sized impact on revenue, margins, or FCF.

5. **Value it — by triangulation, weighted by archetype.** Never a single point estimate.
   Converge on an intrinsic-value *range* from independent lenses, weighted by what the
   archetype makes trustworthy: a **reverse-DCF** ("what growth/margin does today's price
   already imply, and is that achievable?") is first-class — especially for hypergrowth,
   where it is often the *only* honest lens — alongside a forward DCF, an EPV no-growth
   floor, and peer multiples. End with an explicit **margin of safety**. Use the bundled
   `scripts/` and `references/guide_valuation.md`.

   **Discount rate: reason it, don’t default it.** Before running any DCF or EPV, derive
   the discount rate from the business’s actual risk profile — never default to 10% or
   12%. The process: (1) pull betas for 2–4 closest business-model peers from
   `market-scout`, (2) unlever each (Hamada), (3) average to get the peer-group business
   risk, (4) re-lever for the subject’s pro-forma or target capital structure, (5) CAPM
   → cost of equity → WACC, (6) sanity-check against the business description (a
   government-contracted recurring-revenue oligopoly and a single-product biotech do not
   deserve the same rate). The memo’s valuation section **must** include a “Discount Rate
   Derivation” subsection showing this work. See `references/guide_valuation.md` §
   “Discount rate” for the full methodology and common mistakes.

6. **Try to kill it — pre-mortem.** Assume it's a year later and the thesis failed; write
   down why. Run the **archetype's disqualifiers** (each playbook lists them) *and* Lou's
   gate (above). Most candidates should die here or get marked down — that is the system
   working, not failing. Re-tag every surviving claim as verified vs. assumed.

   **Check the institutional ownership picture.** Before finalising the risk assessment,
   pull the 13F holder data. This is a `sec-edgar-skill` script (resolve the path against
   the `sec-edgar-skill` skill directory):
   ```bash
   python scripts/fetch_13f_holders.py --ticker <T> --top 15
   python scripts/fetch_13f_holders.py --ticker <T> --history
   ```
   This reveals who is positioned and how ownership has shifted — signals that feed
   directly into the risk and catalyst assessment:
   - **Concentration risk:** if 3–5 holders own >30% of the float, a single redemption
     cycle can crater the stock independent of fundamentals.
   - **Smart-money conviction:** are high-conviction value managers (Royce, Needham,
     Baupost) building or trimming? A rising share count from a known deep-diver is a
     confirming signal; a quiet exit is a warning.
   - **Activist presence:** a 13D/13G filer showing up in the holder list may signal an
     upcoming catalyst (board fight, strategic review, buyback demand).
   - **Passive vs. active mix:** a stock dominated by index funds (Vanguard, BlackRock,
     State Street) has different liquidity and governance dynamics than one held by
     concentrated active managers.
   - **Ownership trend vs. price:** rising institutional ownership into a falling price
     suggests accumulation; the reverse suggests distribution. Cross-reference with the
     `--history` output.

7. **Reach a verdict at the conviction the work supports.** State the call — **Long /
   Short / Pass / Watch** — with an honest conviction level, the **variant perception**
   (what you believe that the market doesn't, and why you're right), the catalysts or
   monitorables that would confirm or break it, and the margin of safety. If the digging was
   thin, say so and dial conviction down; a hedged verdict is still a verdict.

8. **Write the memo.** Render everything into the standard-DD structure in
   `references/memo_template.md`. The memo *is* the deliverable; pitch-ready is the
   definition of done.

## Archetype routing

Classify in phase 2, then load exactly one playbook (Lou's three shapes are the
value-investing subset; the rest extend past where he worked). Read only the one in play —
each is loaded lazily so you carry just the lens you need.

| If the company is primarily… | Tell by… | Load |
| :-- | :-- | :-- |
| A **quality compounder** — high ROIC, long reinvestment runway | durable returns on capital well above cost, pricing power, low capital intensity | `references/archetypes/compounder.md` |
| A **hypergrowth** name — fast top-line, profits immature | >25–30% growth, heavy S&M, GAAP losses or thin margins, large TAM claim | `references/archetypes/hypergrowth.md` |
| A **cyclical** — earnings swing with a cycle | commodity/industrial/financial exposure, margins that breathe with demand | `references/archetypes/cyclical.md` |
| A **turnaround / inflection** — economics bending on a catalyst | margin or demand inflecting on a regulatory, sectoral, or self-help change | `references/archetypes/turnaround.md` |
| A **special situation** — a structural or legal fact drives it | spin-off, post-bankruptcy, merger/arb, seniority waterfall, squeeze-out | `references/archetypes/special_situation.md` |
| A **deep-value / asset play** — price below tangible value | net cash, net-net, hidden assets, liquidation/sum-of-parts angle | `references/archetypes/deep_value.md` |
| **None fits cleanly** ("anything") | — | Stay on the core spine above; reason from first principles. |

## Driving the tools — the conductor's job

You are the one deciding what the hands fetch. Be deliberate and frugal:

- **Reuse the cache.** `sec-edgar-skill` writes filings to `./sec-cache/{TICKER}/` with
  deterministic, accession-keyed names. `market-scout` caches transcripts to
  `./transcript-cache/{TICKER}/transcripts/`. Before fetching, glob the cache; re-use
  what's there rather than re-hitting the source.
- **Pull by section, not whole filings.** Use item codes (10-K Item 1/1A/7/8) and
  heading maps; grep the cached Markdown and read only the lines that matter. A 10-K can
  exceed 100k words — loading one whole buries the signal.
- **Transcripts are greppable too.** Once cached, grep a transcript for "guidance",
  "margin", a competitor's name, or a specific metric — you don't need to read the whole
  45-minute call to find the passage that matters.
- **13F holder data is live, not cached.** `fetch_13f_holders.py` prints to stdout and
  does not write to disk (ownership data is time-sensitive). Run it when you need it;
  it's one fast HTTP call.
- **Spend tokens where the archetype says the value hides.** Don't fetch a proxy's
  compensation tables for a hypergrowth TAM question, or a deferred-revenue footnote for a
  liquidation. Let the playbook route you.
- **For foreign private issuers** there is no 10-K/10-Q/DEF 14A — it's 20-F and 6-K, and the
  financials are IFRS. `sec-edgar-skill`'s guides cover the mechanics.

If a tool detail is unclear, defer to `sec-edgar-skill`'s and `market-scout`'s own guides
and `--help`; do not re-document the hands here. Keep the tools unopinionated; keep the
opinion in this skill.

## Web research — grounding first, web for the gaps

Filings are the spine of the memo because they are auditable and primary. Reach for the web
only when no filing can answer the question — chiefly *relative* competitive advantage,
real-time market share, pricing dynamics, and channel or customer checks. When you do:
**attribute and date every web claim**, prefer primary sources (company IR, regulators,
trade bodies) over aggregators, and never let a web assertion silently outrank a filing.
Mark web-sourced claims distinctly in the memo so the reader can weight them.

**Do not fire any web search until orient.py has returned and you have read at least one
filing section.** This applies even for breaking news: orient.py will surface the 8-K
filed today, and the 8-K's Exhibit 99.1 is the press release — the primary source that
any web article is merely summarising. Fetch the exhibit; don't search for the summary.

**When a tool errors, recover — don't escape to the web.** A failed `sec-edgar-skill` call —
a fumbled `.to_context()`, a wrong item code, a form that doesn't exist for this issuer — is a
fixable usage detail, not a signal to substitute web search. Re-run `orient.py`, read the
relevant guide, or query `.docs`, then retry. This is the single most common way an analysis
goes wrong: a tool hiccup, a silent pivot to web search, and a thesis built on half-read
aggregator summaries instead of the 8-Ks and 10-Qs that actually exist. The web is a
*supplement for what filings cannot cover* — never a fallback for filings you failed to fetch.
If a recent filing bears on a claim, that filing is the source; a thesis that leans on the web
for something the company's own filings cover is **not yet grounded**, and the verdict's
conviction must reflect that.

## Valuation tooling

Triangulation means doing the same arithmetic every time, so it is scripted — run the
bundled tools rather than hand-rolling a DCF per memo. `--help` is the authoritative flag
reference; one canonical invocation each:

```bash
# Forward two-stage DCF -> intrinsic value per share (accepts comma-separated growth for a
# quick bear/base/bull sensitivity table)
python scripts/dcf.py --fcf0 1200 --growth 8,12,16 --years 10 --terminal-growth 3 \
  --discount 10 --shares 500 --net-debt 200

# Forward three-stage DCF -> when the FCF trajectory has a structural bend: the near-term
# growth rate differs materially from the long-run rate. Add --growth2 and --years2 to
# split the forecast into two explicit phases. Outputs a stage-1 x stage-2 sensitivity
# matrix. Common uses: turnaround cost-out, hypergrowth investing-then-harvesting,
# cyclical recovery, post-acquisition synergy ramp, regulatory deployment wave.
python scripts/dcf.py --fcf0 5 --growth 25,35,50 --years 3 \
  --growth2 5,8 --years2 7 --terminal-growth 2.5 --discount 12 \
  --shares 30 --net-debt 66 --price 2.75

# Reverse DCF -> the stage-1 growth the current price already implies ("what's priced in")
python scripts/dcf.py --mode reverse --price 150 --fcf0 1200 --years 10 \
  --terminal-growth 3 --discount 10 --shares 500 --net-debt 200

# Earnings Power Value -> the no-growth floor (a triangulation anchor)
python scripts/epv.py --ebit 600 --tax 21 --wacc 9 --shares 500 --net-debt 200
```

`references/guide_valuation.md` explains which lens to weight for which archetype, how to set
the discount rate and terminal value honestly, and how to read a reverse-DCF result.

## Bundled resources

| Resource | When to read / run |
| :-- | :-- |
| `references/memo_template.md` | The required output structure. Read before writing the memo. |
| `references/guide_normalization.md` | Phase 3 — un-distorting the financials into owner earnings. |
| `references/guide_competitive.md` | Phase 4 — SEC-first competitive work; when to go to the web. |
| `references/guide_valuation.md` | Phase 5 — triangulation, reverse-DCF, discount/terminal discipline. |
| `references/archetypes/*.md` | Phase 2 — load the one matching the company's shape. |
| `scripts/dcf.py`, `scripts/epv.py` | Phase 5 — the valuation arithmetic. `--help` for flags. |

## The two questions every memo must pass

Before you ship, ask the two questions the best write-ups always pass:

1. *Is every claim here something I actually verified in a document or computed myself —
   and is everything I didn't verify marked as such?*
2. *Have I been as honest and specific about what's wrong with this as I am about what's
   right?*

If yes to both, the memo is pitch-ready.
