---
name: pitch-like-lou
description: >-
  Write or rewrite a stock pitch the way Norbert Lou did in his legendary Value Investors Club
  write-ups — numbers-first, high-conviction value investing. Use this skill whenever the user
  wants to make the bull or bear case for a stock, draft an investment thesis or write-up,
  argue a long or short in a value-investing voice, or whenever Norbert Lou or Value Investors
  Club (VIC) is mentioned. Also use it when asked to "pitch me on X", "write up this stock",
  "convince me this is a buy/sell", "make the case for X", or render a finished thesis as a
  short, compelling pitch. Pairs with SEC-filing tools for the raw numbers.
---

# Pitch Like Norbert Lou

This skill teaches the *craft* behind Norbert Lou's pitches: where he dug, what he refused to
ignore, and how he wrote the verdict so plainly that a skeptic kept reading. It is a lens and a
voice — not an idea generator.

Be honest with yourself about what makes those pitches great. Read enough of them and the same
truth keeps surfacing: the edge is **situation-specific forensics on primary documents** (the
put/call formula buried in Schedule 1.04 of a Quinsa exhibit; a $750M pink-sheet preferred that
sits *senior* to $30B of WorldCom bonds; a subscription liability that makes GAAP understate real
earnings). No checklist produces those. What a skill *can* carry is the disposition that points
you at them and the voice that renders them. That is this skill's job. The insight itself comes
from you, reasoning over the actual filings.

## What this is — and is not

- **It is:** a *disposition* (where value tends to hide, what to read, what to normalize) welded
  to a *voice* (how Lou structures and argues a pitch, and the temperament that makes it credible).
- **It is not:** a screener, an "analysis engine," or a promise that a stock is good. It will not
  hand you a thesis, and it must never **manufacture conviction you have not earned by doing the work.**
- **The seam:** the raw material — financials, footnotes, proxies, ownership, deal documents — comes
  from your SEC-filing tools (the `sec-edgar-skill` skill's `fetch_filing` / `parse_financials`),
  and price / peer data from the `market-scout` skill's `fetch_market_data`. This skill tells you
  *which* of those to pull and *why*; it does not re-document them. Keep the tools unopinionated;
  keep the opinion here.

## The one inviolable rule: never let the voice outrun the evidence

Lou's prose is persuasive *because* it is backed by forensic work and radical honesty about the
weak spots. Borrow his cadence and confidence onto a thesis you have not investigated and you have
built a machine for sounding right while being wrong — the exact failure this skill exists to avoid.

So the temperament below is not decoration. It is the safety mechanism. If you have not done the
digging, **say so and dial the conviction down.** A Lou pitch with hedges is still a Lou pitch; a
Lou pitch with borrowed certainty is propaganda.

A cautionary tale from the corpus itself: in the MCI QUIPS pitch — a brilliant structural-seniority
thesis — Lou relayed *third-hand* that the books were clean with no material intercompany payables.
A forensic accountant later surfaced ~$24 billion of intercompany claims that nearly sank the trade
on a substantive-consolidation fight; the position was down ~68% at the trough before it resolved.
Even his best work had a blind spot at exactly the point where he leaned on something he had not
verified himself. The lesson is not "be timid" — it's *know which of your claims you actually
checked, mark the ones you didn't, and follow through honestly when a thesis turns against you.*

## The loop

1. **Classify the situation.** Almost every Lou idea is one of three shapes:
   *quality compounder*, *cigar-butt asset play*, or *special-situation / structural arbitrage*.
   The shape decides where you dig and which parts of the pitch carry the weight.
2. **Dig where that shape pays** — using your SEC tools. See **Where to dig**.
3. **Try to kill it.** Lou posts maybe one idea a year; the discipline is mostly *saying no*. Run
   the disqualifiers before you fall in love. Most candidates die here, and that is the system working.
4. **Render** it in the structure and voice below — but only at the conviction your digging supports.

## The voice — the part that is actually him

Each move below earns its place; the parenthetical is *why* it works. Short quotes are illustrative.

- **Lead with the punchline, usually a number.** No "I am pleased to present." Open on the
  disconnect. (*"Winmill & Company has net cash of $3.91. The stock trades for $1.70."* The reader
  is hooked before any throat-clearing could lose them.)
- **Pre-empt the biggest objection in the second sentence, then invert it.** (*"Yes, pink sheet
  equities in bankrupt companies are worthless 99.9% of the time. There are special features,
  however…"* — disarming the obvious dismissal buys you the rest of the page.)
- **Plain, declarative, numbered. Define your terms inline.** Spell out *FCF = operating cash flow
  minus capex*; *net cash = cash and securities minus ALL liabilities*. (Precision is itself an
  argument; it signals you did the work and pre-empts a fight over definitions.)
- **Earn conviction through honesty, not adjectives.** Separate *what you know* from *what you
  believe*. Concede the weak points out loud. When governance is ugly — option grants, insider
  pay — do not wave it away: **estimate the cost of the "value-destructive" actions, subtract it
  from your value, and demand a margin of safety that survives anyway.** (*"His mansion was paid
  for with wheelbarrows of liberally-issued stock options"* — admitting the flaw is what makes the
  bullishness believable.)
- **Signal credibility by being unimpressed with yourself.** Post rarely; admit when your own price
  target was laughably low; never hype. (*"I included a target of $28.10… so it shows how much I
  know"* — self-deprecation builds trust faster than a swagger ever could.)
- **Answer a risk with judo, not denial.** Acknowledge the *real* version of the objection, then
  show it applies equally to something the skeptic already loves. (On emerging-market currency fear:
  isn't it curious nobody asks about the same dollar-liability/foreign-revenue mismatch at Coke?)
- **Use one homely analogy to collapse a hard idea.** A deep discount to liquid assets behind a
  controlling family becomes *a money-market fund holding $1.50 in cash, locked up for five years —
  would you buy it for 40 cents?* Spectrum licenses become *cable-franchise or broadcast rights.*
  (One concrete image does the work of a page of exposition.)
- **Intrinsic value only; ignore the chart.** A price decline is not a warning, it is a cheaper
  entry. Never reason from the tape.
- **Quiet wit, used once.** (*"It's this fancy new thing called the internet."*) Sparingly — it
  flatters the reader and mocks the market's blind spot without breaking the analytical tone.

## The structure — a shape that serves the argument, not a template to fill

Use the skeleton, but let the *situation* decide where the weight goes. A cigar-butt leans on
questions 1 and 4; a compounder on 2 and 3; an arbitrage on 1 and 4 with the structural fact as
the spine. Do not pad a section just because it exists.

### 1. Stat header
A compact, text-aligned block of the core metrics. Keep it; it orients the reader instantly.
```text
Price: [px]                    EPS: [cur / fwd]
Shares Out (M): [sh]           P/E: [x]
Market Cap ($M): [mc]          P/FCF: [x]
Net Debt ($M): [nd]            EBIT: [ebit]
TEV ($M): [tev]                TEV/EBIT: [x]
```
*Calc discipline:* Net Debt = total debt − cash & marketable securities. TEV = market cap + net
debt + the cost of option dilution (treasury-stock method — bake the dilution in, don't footnote it).
FCF = operating cash flow − capex, and **name any adjustment you make** rather than burying it.

### 2. The hook
One paragraph. State the core disconnect in the first breath.
- *Compounder:* lead with the return-and-multiple gap — *"…an unleveraged return on equity of over
  35% and trades at 4.85x free cash flow."*
- *Asset play / arb:* lead with the value-to-price gap and the reason it's safe — *"…net cash of
  $3.91 … trades for $1.70 … If the stock trades to net cash, the total return will be 130%."*

### 3. The body — the four questions a Lou pitch actually answers
Write these as argument, not headings to check off:
1. **Why is it this cheap — and why is that fear wrong?** Name the market's reason (cyclical,
   post-bankruptcy neglect, EM currency, "value trap") and dismantle it. For asset plays, prove
   there is no catch — the usual culprits are funded debt or an operating burn depleting the cash,
   so show that neither applies.
2. **What is the engine, or the hard fact?** Compounders: the moat — local scale, lowest-cost
   production, "share of mind" brand, switching costs — explained mechanically, not asserted.
   Special situations: the structural fact — the seniority waterfall, the put/call formula, the
   minority-protection statute — explained so a non-specialist sees why it nearly *has* to resolve.
3. **What do the numbers say, once they're honest?** ROIC, capex intensity, working-capital
   behavior — after you un-distort the accounting. Show the capital-allocation track record as a
   **year-by-year table** (the falling share count, the deleveraging), because the trend persuades
   where a single number does not.
   ```text
   12/31/95: 15.21M shares    12/31/98: 10.39M
   12/31/96: 13.57M           12/31/99:  9.17M
   12/31/97: 11.09M           04/18/01:  8.14M
   ```
4. **Who controls the outcome, and are incentives aligned?** Controlling family, founder's age and
   estate, the put/call or takeover formula, the option pool. Price the bad parts in as a cost of
   ownership; map why the decision-maker is likely to do the value-realizing thing.

### 4. The catalyst
A short numbered list of specific, near-dated events that close the gap — a buyback authorization,
an exchange uplisting, a founder's retirement, a put/call exercise date, price hikes hitting next
quarter's margins. Vague "re-rating" is not a catalyst; a date or a mechanism is.

## Where to dig — route each shape to your SEC tools

This is the disposition, kept thin on purpose. It tells you *what to pull and what to normalize*;
your filing tools do the pulling. (Tool names below refer to the `sec-edgar-skill` skill; adapt to
whatever hands you have.)

| Situation | Where the value hides | Read (pull these) | Normalize / adjust | Disqualifiers (kill it if…) |
|---|---|---|---|---|
| **Compounder** | un-distorted ROIC/FCF, a secular cost shift, buyback math | 10-K Item 7 (MD&A) & Item 8; the cash-flow statement; revenue/lease/deferred-revenue footnotes; the proxy (comp) | capex → maintenance level; pull deferred revenue back into earnings; undo treasury-stock-as-asset quirks | growth needs new capital; ROIC is an accounting mirage; buybacks happen only when the stock is dear |
| **Cigar-butt asset play** | price vs. net cash, proof of "no catch," a realization catalyst | balance sheet & liability footnotes; recent 8-Ks (asset sales); proxy (founder age, ownership) | subtract **all** liabilities; back non-recurring items out of operating cash flow; haircut value-destructive options | funded debt, or operating cash burn that eats the pile; no plausible catalyst; the discount is smaller than the governance theft |
| **Special situation / arb** | a structural or legal fact (seniority waterfall, put/call formula, squeeze-out law) | the agreement / indenture / 13D exhibit itself; reorg or plan docs; 20-F & 6-K for foreign issuers; the foreign regulator's filings | compute the formula *yourself*; rebuild the post-event capital structure; reconcile foreign-GAAP to a comparable basis | the legal fact doesn't actually bind; minorities have no protection; the timeline is open-ended with no forcing event |

For the mechanics of pulling any of these (item codes, sections, exhibits, XBRL financials), defer
to your filing tools — don't reinvent them here. The 8-K's fired items tell you *what happened*;
the 13D's `item4_purpose_of_transaction` tells you *why*; the proxy and ownership forms map the
incentives. Note for foreign private issuers: there is no 10-K/10-Q/DEF 14A — it's 20-F and 6-K,
and the financials are IFRS.

## Calibrating from the real pitches

The seven primary sources ship with this skill in `references/corpus/` — each is the full VIC
write-up plus its discussion thread. They are the ground truth for the voice, but they run several
thousand words each, so treat them like a big filing: **don't load them wholesale.** When you need
to nail a specific move — a hook, a rebuttal, a stat header, a buyback table — grep the corpus for
it and read just the matching lines, the same way you'd pull one section out of a 10-K.

- **Compounder:** `NVR`, `Sportsman's Guide`
- **Cigar-butt asset play:** `Winmill`
- **Special situation / structural arbitrage:** `Quilmes` (put/call + squeeze-out), `MCI` (capital-structure
  seniority), `NII Holdings` (post-bankruptcy neglect), `Telemig` (emerging-market minority buyout)

Each file has the write-up *and* the full discussion thread. The threads are where the temperament
is most visible — watch how he concedes points, separates what he knows from what he suspects,
answers a hostile question without flinching, and (in MCI) handles a thesis going wrong. Calibrate
your *honesty* there, not just your bullishness.

When in doubt about whether a sentence is "Lou enough," ask the two questions his best writing
always passes: *Is every claim here something I actually verified in a document?* and *Have I been
as honest about what's wrong with this as I am excited about what's right?* If yes to both, ship it.
