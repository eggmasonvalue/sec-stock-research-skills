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

### 5. Competitive position & industry
Industry structure, the company's place in it, and *relative* competitive advantage —
moat (or its absence) explained mechanically, not asserted. Ground in filings (incl. peers'
filings); use web only for what filings can't give, and mark it [W].

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

### 7. Risks & pre-mortem
The bear case, in your own words and as strong as you can make it. Run the archetype's
disqualifiers explicitly. Assume it's a year out and the thesis failed — what broke?
Re-tag the load-bearing claims as verified vs. assumed; the assumed ones are your risks.

### 8. Catalysts & monitorables
Specific, ideally dated events or metrics that would confirm or break the thesis — a
buyback, an uplisting, a margin-inflection quarter, a cohort metric, a regulatory date.
"Re-rating" is not a catalyst; a mechanism or a date is. List what you'll watch to know if
you're wrong early.

### 9. Verdict & conviction
The call — **Long / Short / Pass / Watch** — at the conviction the work supports, with a
one-line rationale tying back to the variant perception and the margin of safety. If the
digging was thin in places, say where; an honest hedge is part of the verdict.

### 10. Appendix — sources
The audit trail. Every filing used (form + accession number + section) and every web source
(URL + date). This is what makes the memo checkable — and what a downstream pitch leans on
when a skeptic pushes back.
