# Valuation — triangulation, weighted by archetype

Phase 5 of the loop. Value is a *range*, reached from independent lenses, never a single
false-precision point. Each lens has failure modes; the archetype tells you which to trust.
The discipline is to make every assumption explicit and conservative enough that the thesis
survives the *low* end — an intrinsic value that only works on heroic inputs is a hope, not a
valuation.

Run the arithmetic with the bundled scripts (`scripts/dcf.py`, `scripts/epv.py`) rather than
re-deriving it each time; `--help` is the flag reference. Reason about the *inputs* here.

## The four lenses

### 1. Reverse-DCF — "what's already priced in" (first-class)
Instead of forecasting, **invert**: solve for the stage-1 growth (or margin) the *current
price* requires, then ask one question — *is that achievable?* This is the most honest lens
when the future is uncertain, and for **hypergrowth** names it is often the *only* defensible
one: rather than pretend you can forecast a hyper-growth decade, you judge whether the
market's embedded expectation is too high, about right, or too low. Run it on every name as a
reality check, even when another lens leads.

```bash
python scripts/dcf.py --mode reverse --price 150 --fcf0 1200 --years 10 \
  --terminal-growth 3 --discount 10 --shares 500 --net-debt 200
```
Read the result against reality: if the price implies 22% FCF growth for a decade and the
company has never exceeded 12%, the bar is too high regardless of how good the story sounds.

### 2. Forward DCF — intrinsic value under your assumptions
A two-stage discounted cash flow on normalized owner earnings (phase 3). Best for businesses
with *predictable* cash flows — compounders, stable cash generators. Drive it with
**bear/base/bull** growth cases (the script accepts comma-separated growth for a quick
sensitivity table) so the output is a range, not a point.

```bash
python scripts/dcf.py --fcf0 1200 --growth 8,12,16 --years 10 --terminal-growth 3 \
  --discount 10 --shares 500 --net-debt 200
```

When the FCF trajectory has a **structural bend** — the near-term growth rate differs
materially from the long-run rate — a single stage-1 rate is a forced average that
misrepresents both phases. Use the **three-stage model** by adding `--growth2` and
`--years2`. Stage 1 captures the distinct near-term phase, stage 2 captures the subsequent
normalized phase, then the terminal value. The output is a stage-1 × stage-2 sensitivity
matrix. Reach for it whenever the business has an identifiable reason for the growth rate
to change — not just turnarounds, but any shape where one rate doesn’t fit:

- **Turnaround / inflection:** cost-outs, margin expansion, or debt paydown free up FCF
  faster than revenue grows (stage 1), then revenue-driven growth takes over (stage 2).
- **Hypergrowth investing phase:** heavy S&M/R&D depresses FCF now; once the business
  scales past the investment hump, FCF inflects sharply (stage 1), then grows at a
  mature-compounder rate (stage 2).
- **Cyclical recovery:** earnings snap back from trough to mid-cycle (stage 1), then grow
  at trend (stage 2).
- **Regulatory / deployment wave:** a defined tailwind (NG9-1-1 rollout, 5G buildout)
  drives elevated growth for a bounded period (stage 1), then steady-state (stage 2).
- **Post-acquisition synergies:** integration savings land over 2–3 years (stage 1),
  then organic growth resumes (stage 2).

```bash
python scripts/dcf.py --fcf0 5 --growth 25,35,50 --years 3 \
  --growth2 5,8 --years2 7 --terminal-growth 2.5 --discount 12 \
  --shares 30 --net-debt 66 --price 2.75
```

### 3. EPV — the no-growth floor
Earnings Power Value capitalizes *current normalized* operating earnings with **no growth
credit** — a conservative floor that answers "what's it worth if the growth never shows up?"
Especially clarifying for cyclicals (use mid-cycle EBIT), deep-value, and any case where you
don't want to pay for a future you can't underwrite.

```bash
python scripts/epv.py --ebit 600 --tax 21 --wacc 9 --shares 500 --net-debt 200
```

### 4. Relative multiples — the sanity check
P/E, EV/EBIT, EV/Sales, P/FCF against the peer set (`market-scout` gives you the peers).
Never a thesis on its own — "cheap vs. peers" can mean the whole group is
mispriced or the company deserves its discount — but a vital cross-check on the absolute
lenses, and the right primary lens for some special situations and asset plays.

## Setting the inputs honestly

The output is only as good as three judgment calls — show your work on each:

- **Discount rate.** See the dedicated section below — this is the input most analysts get
  wrong, and it deserves its own reasoning process.
- **Terminal value.** This is usually most of a DCF's value, so it's where false precision
  hides. Keep terminal growth at or below long-run GDP; sanity-check the implied terminal
  multiple — if it bakes in a permanent premium multiple, you've smuggled optimism into the
  tail.
- **The base cash flow.** Use *normalized* owner earnings (phase 3), not a peak or trough
  year. Garbage in, garbage out — most valuation errors are bad inputs, not bad arithmetic.

## Discount rate — reason it, don't default it

The discount rate is the single most levered input in a DCF: a 300bps change can move
intrinsic value by 30–50%. Yet it is the input most often set by reflex (“10% for
equity”) rather than by reasoning. **Every memo must derive and justify its discount rate
in a dedicated subsection of the valuation section.** A number without a rationale is an
assumption the reader cannot audit — and cannot trust.

### The reasoning process (do this every time)

1. **Start with the business, not the stock.** Ask: *what is the risk profile of the
   underlying cash flows?* A government-contracted, recurring-revenue oligopoly with
   mandated demand has fundamentally different cash-flow risk than a single-product
   biotech or a commodity cyclical. The business risk should drive the unlevered cost of
   capital — the stock’s trading volatility and capital structure are layered on top.

2. **Anchor to peers, not defaults.** Pull betas for 2–4 closest business-model peers
   from `market-scout` (yfinance’s `.info["beta"]`). Unlever each using Hamada:
   `beta_u = beta_l / (1 + (1 - tax_rate) * D/E)`. Average the unlevered betas — this
   is the *business risk* of the peer group, stripped of each company’s financing
   choices.

3. **Re-lever for the subject’s capital structure.** Use the company’s *pro-forma or
   target* D/E (not necessarily today’s, if the capital structure is in transition):
   `beta_l = beta_u * (1 + (1 - tax_rate) * D/E)`. Then CAPM:
   `Ke = Rf + beta_l * ERP`. Use the current 10-year Treasury yield for Rf and a
   long-run ERP of 5–6% (Damodaran’s implied ERP is the standard reference).

4. **Compute WACC if doing an enterprise DCF.** Weight cost of equity and after-tax
   cost of debt by their shares of total capital. If there is preferred equity or
   mezzanine debt, include it as a separate tranche at its own cost.

5. **Sanity-check against the business description.** Before using the number, ask:
   *does this rate make sense for what this business actually is?* A few guideposts:

   | Business type | Typical WACC range | Why |
   | :-- | :-- | :-- |
   | Regulated utility / infrastructure concession | 6–8% | Contracted, inflation-linked, near-monopoly |
   | Mission-critical gov-contracted recurring revenue | 8–10% | Mandated demand, high switching costs, oligopoly |
   | Stable consumer/enterprise compounder | 9–11% | Durable moat, predictable FCF |
   | Cyclical industrial / commodity | 10–13% | Earnings volatility, capital intensity |
   | Growth-stage / unproven unit economics | 12–15% | Execution risk, cash burn, TAM uncertainty |
   | Distressed / binary outcome | 15%+ | Survival risk, option-like payoff |

   If your derived WACC lands far outside the range for the business type, re-examine
   your inputs — the beta sample, the D/E assumption, or the ERP. The guideposts are
   not rules, but a derived rate that contradicts the business description is a red flag.

6. **Separate business risk from financial risk.** When the capital structure is
   distressed or in transition (turnarounds, post-divestiture, over-leveraged), the
   *business* may deserve a low discount rate while the *equity* deserves a high one.
   Make this explicit: run the DCF at the business-appropriate WACC to value the
   enterprise, then subtract net debt and senior claims to get equity value. Do not
   double-count by using a high WACC *and* subtracting the debt — that penalizes the
   cash flows for leverage risk and then penalizes the equity again.

7. **State it in the memo.** The valuation section must include a subsection titled
   “**Discount Rate Derivation**” (or similar) that shows: the peer set used, their
   betas and unlevered betas, the re-levered beta, the CAPM cost of equity, the WACC,
   and the sanity check against the business description. A reader should be able to
   disagree with your rate and re-run the DCF with their own — that’s the point.

### Common mistakes

- **Defaulting to 10% or 12%.** These are not reasoned rates; they are habits. 10% was
  a reasonable equity return assumption when the risk-free rate was 4–5% and the ERP was
  5–6%, but it says nothing about *this specific business*. Always derive.
- **Using the stock’s own beta.** A distressed, thinly-traded small-cap will have a
  high beta driven by liquidity and sentiment, not business risk. Use peer unlevered
  betas to isolate the business risk, then re-lever.
- **Double-counting leverage risk.** If you use a high WACC because the company is
  leveraged, and then also subtract a large net-debt figure, you’re penalizing leverage
  twice. The WACC already reflects the cost of the debt; subtracting net debt converts
  enterprise value to equity value. Don’t inflate both.
- **Ignoring capital structure transitions.** A turnaround that will be nearly debt-free
  in 18 months should not be discounted at today’s levered cost of capital for a
  10-year DCF. Use the *target* or *normalized* capital structure for the WACC, and
  reflect the transition costs in the near-term cash flows instead.

## Weighting by archetype

Lean on the lens the business actually fits; report the others as cross-checks.

| Archetype | Lead lens | Cross-check with |
| :-- | :-- | :-- |
| Compounder | Forward DCF (long stage-1 runway) | Reverse-DCF reality check; EPV floor |
| Hypergrowth | **Reverse-DCF** (what's priced in) | Multiples; scenario forward DCF |
| Cyclical | EPV on **mid-cycle** earnings | Normalized P/E; mid-cycle multiples |
| Turnaround / inflection | Scenario DCF (post-inflection margins) | EPV today as downside floor |
| Special situation | Event payoff / sum-of-parts | Multiples on the resulting pieces |
| Deep value | Asset value / liquidation; EPV floor | Multiples; reverse-DCF for the catalyst |

## The output

A defensible **intrinsic-value range** (low–high, anchored to bear–bull), the **margin of
safety** at today's price, and a plain statement of the *one or two assumptions the value is
most sensitive to* — because that's where the next reader (and reality) will push hardest.
Carry these straight into the verdict.
