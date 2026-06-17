# The memo — standard due-diligence structure

This is the deliverable. The memo *is* the product of the whole loop, and "pitch-ready"
is the definition of done: complete and honest enough that a `pitch-like-lou` pitch could
stand on it without inventing anything.

A memo is an argument, not a form. Use this structure as a skeleton, but let the
**archetype** decide where the weight goes — a compounder earns its keep in the economics
and moat sections; a special-situation in the structural fact and the payoff; a hypergrowth
name in the reverse-DCF and unit economics. Do not pad a section to fill it. A tight
six-page memo beats a padded twenty.

## The honesty markup (use it throughout)

The single most important habit: let the reader audit your confidence. Adopt a consistent
convention and use it in every section — for example:

- **[V]** verified — you read it in a named filing (give the form + accession or section).
- **[E]** estimate — you computed or modeled it; state the assumption.
- **[A]** assumption — you're taking it on faith; flag it for the reader to challenge.
- **[W]** web — sourced from outside filings; attribute and date it.

The markup is not bureaucracy. It is what separates a memo from propaganda: a reader can see
at a glance which load-bearing claims are solid and which are your judgment.

## Structure

### 0. Stat header
A compact, text-aligned block that orients the reader in five seconds. Compute, don't
guess; name any adjustment.

```text
Ticker / Name            Price: [px]            Archetype: [one of the six]
Market Cap ($M): [mc]    EPS (cur/fwd): [ ]     Verdict: [Long/Short/Pass/Watch]
Net Debt ($M): [nd]      P/E: [x]               Conviction: [Low/Med/High]
TEV ($M): [tev]          P/FCF: [x]             IV range: [low–high]
Shares (M, dil): [sh]    TEV/EBIT: [x]          Margin of safety: [%]
```
*Calc discipline:* Net Debt = total debt − cash & marketable securities. TEV = market cap +
net debt + cost of option dilution (treasury-stock method — bake it in, don't footnote it).
FCF = operating cash flow − capex, with any normalization named.

### 1. Thesis & variant perception
Three to five sentences, punchline first. The core disconnect, then the **variant
perception**: what do you believe that the market doesn't, and *why are you the one who's
right*? If you can't name a variant perception, you have a description, not a thesis.

### 2. Business overview
How the company actually makes money — segments, unit of sale, who pays and why, revenue
model, key economics — in plain language. If you can't explain it in one clean sentence,
you're not ready to value it.

### 3. Archetype & why it's the right lens
Name the primary (and any secondary) archetype and justify it from the financials and
business model. This tells the reader which questions the rest of the memo prioritizes.

### 4. Financial analysis — the normalized economics
The un-distorted earning power (see `guide_normalization.md`), not raw GAAP. Owner earnings
/ FCF, returns on capital, margins and their drivers, working-capital behavior. Include the
**capital-allocation track record as a year-by-year table** — share count, debt,
reinvestment and the return on it — because the trend is the argument.

**When the thesis depends on a new revenue stream** (pre-revenue JV, partnership product,
market entry enabled by a regulatory change, post-restructuring margin profile), include a
**unit-economics bridge** that builds from per-unit inputs (price, cost, volume) to the
stream’s contribution to FCF. A management TAM estimate plugged into a DCF growth rate is
not a model — it is a hope with a discount rate. See `guide_normalization.md` § “When the
thesis depends on a new revenue stream.”

### 5. Competitive position & industry
Industry structure, the company's place in it, and *relative* competitive advantage —
moat (or its absence) explained mechanically, not asserted. Ground in filings (incl. peers'
filings); use web only for what filings can't give, and mark it [W].

**Quantify, don't catalogue.** Every competitive strength, moat mechanism, and threat must
be sized — how big, how fast it's moving, and what the dollar impact on *this company*
would be if it plays out. “High switching costs” is a label; “3-year migration timelines
and 95%+ renewal rates” is evidence. “Competition is intensifying” is mood; “Competitor X
grew Y% last year and now holds Z% of the addressable market” is a fact the reader can
reason from. A competitive force you can’t size is one you haven’t understood — mark it
[A] and flag the gap. See `guide_competitive.md` § “Quantify impact.”

### 6. Valuation
Triangulated, never a single point (see `guide_valuation.md`). Show each lens, weighted by
archetype, including a **reverse-DCF of what today's price implies**. Lay out
**bear / base / bull** scenarios with their key assumptions, converge on an **intrinsic-value
range**, and state the **margin of safety** at the current price.

This section **must** include a subsection titled **"Discount Rate Derivation"** (or
similar) that shows the reasoning behind the discount rate used in the DCF and EPV. The
subsection should show: the peer set used for beta benchmarking, their levered and
unlevered betas, the re-levered beta for the subject company's capital structure, the
resulting CAPM cost of equity, the WACC, and a sanity check against the business
description (see `guide_valuation.md` § "Discount rate" for the full methodology). A
discount rate without a derivation is an unauditable assumption — the reader cannot
disagree with it, which means they cannot trust it.

### 7. Ownership — institutional holders and insider activity
Who owns this stock — from the outside and from the inside — and what does the
ownership picture tell you about alignment, adverse selection, and risk?

**Institutional holders.** Pull from `sec-edgar-skill`'s
`scripts/fetch_13f_holders.py`. Include:
- **Top holders** (top 10–15 by shares) and whether they are passive index funds or
  active/concentrated managers.
- **Ownership trend** — is institutional ownership rising or falling? Cross-reference
  with price to distinguish accumulation from distribution.
- **Notable holders** — any known deep-value, activist, or sector-specialist funds?
  Their presence (or absence/exit) is a signal.
- **Concentration risk** — if a handful of holders dominate the float, flag the
  liquidity and forced-selling risk.

**Insider ownership and activity.** Pull from `sec-edgar-skill`'s
`scripts/fetch_insider_trades.py`. Include:
- **Recent insider transactions** — a table of open-market purchases and sales over
  the past 6–12 months. Distinguish voluntary open-market trades (code P/S) from
  routine option exercises (M) and tax withholdings (F).
- **Buy/sell ratio** — are insiders net buyers or net sellers? A strong buy/sell ratio
  is a confirming signal; net selling into your long thesis is an adverse-selection
  warning.
- **Key buyers/sellers** — name the individuals and their roles. A CEO buying $1M of
  stock carries more weight than a director buying $20K.
- **Ownership level** — how much do insiders own in aggregate? Cross-reference
  remaining holdings against compensation (from the proxy) to gauge skin in the game.
- **FPI note** — if the company is a foreign private issuer exempt from Section 16,
  state that Form 4 data is unavailable and note any home-jurisdiction disclosures
  found (or the gap, if none).

This section is short (a table or two + a paragraph of interpretation per sub-topic),
but it grounds the catalyst and risk sections that follow. The insider picture in
particular is a direct check on adverse selection — if the people with the best
information are not aligned with your thesis, that fact belongs in the risk section.

### 8. Risks & pre-mortem
The bear case, in your own words and as strong as you can make it. Run the archetype's
disqualifiers explicitly. Assume it's a year out and the thesis failed — what broke?
Re-tag the load-bearing claims as verified vs. assumed; the assumed ones are your risks.

**Every risk must pass the “so what” test.** State the *impact* — what happens to
revenue, margins, or FCF if this risk materializes, and over what timeframe? A risk
without a sized impact is a worry, not an analysis. Where possible, assign a probability
(High/Medium/Low) and cite the evidence behind it. The pre-mortem narrative should
reference the sized risks from the competitive section, not re-invent them as vague
fears.

### 9. Catalysts & monitorables
Specific, ideally dated events or metrics that would confirm or break the thesis — a
buyback, an uplisting, a margin-inflection quarter, a cohort metric, a regulatory date.
"Re-rating" is not a catalyst; a mechanism or a date is. List what you'll watch to know if
you're wrong early.

### 10. Verdict & conviction
The call — **Long / Short / Pass / Watch** — at the conviction the work supports, with a
one-line rationale tying back to the variant perception and the margin of safety. If the
digging was thin in places, say where; an honest hedge is part of the verdict.

### 11. Appendix — sources
The audit trail. Every filing used (form + accession number + section) and every web source
(URL + date). This is what makes the memo checkable — and what a downstream pitch leans on
when a skeptic pushes back.
