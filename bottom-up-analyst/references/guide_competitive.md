# Competitive & industry analysis - filings first, web for the gaps

Phase 4 of the loop. A normalized earnings number is only as trustworthy as the moat under
it: durable returns require a durable *reason*. This phase establishes industry structure,
the company's place in it, and - the hard, decisive part - its **relative** competitive
advantage. Assert nothing; explain the moat *mechanically* or concede there isn't one.

The governing rule of the stack applies here with full force: **SEC filings are the default
and the grounding; the web fills only what filings genuinely cannot.** Filings are primary,
auditable, and citable; the web is a labeled supplement that must never silently outrank a
filing.

## What filings give you - more than people expect

Before touching the web, exhaust the documents. A surprising amount of "qualitative" insight
is sitting in EDGAR, already auditable:

- **The subject's 10-K.** Item 1 (Business) describes competition, customers, suppliers, and
  segments in the company's own words. Item 1A (Risk Factors) is a candid map of what
  management fears - read it as a competitive document, not boilerplate. The MD&A (Item 7)
  explains *why* the numbers moved.
- **Peers' own filings - the high-leverage move.** `market-scout` hands you the **peer
  set**. Pull each peer's recent **8-Ks, 10-Qs, and 10-K** and read
  their management commentary: pricing actions, demand color, capacity, who's winning share.
  Triangulating the same quarter across three competitors' filings is primary-source
  competitive intelligence you can cite [V] - often sharper than any third-party take.
- **Industry structure from the numbers.** Compare gross and operating margins, returns on
  capital, capital intensity, and growth across the peer set. Persistent margin or ROIC
  gaps are the *quantitative fingerprint* of a moat (or its absence) - pricing power, scale
  economics, switching costs show up here before anyone writes them down.

## What only the web can give - and how to use it

Some questions no filing answers, and these are exactly where competitive theses are won or
lost. Go to the web for:

- **Relative positioning and market share** - who's actually winning, and the trend.
- **Pricing dynamics and channel checks** - real-world price moves, distribution, customer
  satisfaction, churn anecdotes.
- **Industry tailwinds/headwinds** - regulation, technology shifts, end-market demand.
- **Management quality and track record** - beyond the proxy's bare facts.

When you do, observe the discipline that keeps the memo trustworthy:

- **Attribute and date every web claim**, and prefer **primary** sources - company IR decks,
  regulators, standards bodies, trade associations - over aggregators and secondary
  commentary.
- **Mark it [W]** in the memo so the reader can weight it differently from a filed fact.
- **Never let a web assertion override a filing** without saying so explicitly and explaining
  why you believe the web over the document.
- **Separate fact from sentiment.** "Revenue grew 30%" (checkable) is not "analysts love the
  story" (mood). Both can matter; don't let the second masquerade as the first.

## The output of this phase

A clear verdict on competitive position you can defend:

1. **Industry structure** - concentration, rivalry, where the profit pools sit, the
   secular direction of travel.
2. **The company's position** - leader/challenger/niche, and the *evidence* (the margin/ROIC
   gap vs. peers, share trend, customer captivity).
3. **The moat, named and tested** - which specific mechanism (scale, network, switching
   costs, brand/share-of-mind, low-cost production, regulatory) and *why it persists*. State
   what would erode it; a moat you can't imagine breaching is a moat you haven't examined.

Feed this straight into valuation: the strength and *durability* of the moat is what justifies
the growth runway and the discount rate you'll defend in phase 5.

## Quantify impact, don't just list forces

The most common failure in competitive analysis is **cataloguing without quantifying.**
Listing five barriers to entry or four competitive threats is not analysis - it is
inventory. The reader needs to understand *how much each force matters* to the thesis.
For every competitive strength, weakness, threat, or moat mechanism, answer three
questions:

1. **How big is it?** Attach a number, a share, a dollar figure, or a rate. "High
   switching costs" is a label; "multi-year contracts with 95%+ renewal rates and
   12-18 month migration timelines" is evidence. "Competition is intensifying" is mood;
   "Motorola's Command Center division grew 14% last year and now holds ~30% of the
   call-handling market" is a fact you can reason from.

2. **How fast is it moving?** A static snapshot is not enough. Is the competitor
   gaining share, losing it, or flat? Is the technology threat emerging (R&D stage),
   arriving (first deployments), or mature (already displacing incumbents)? A threat
   that is five years away at current pace is a different input to the thesis than one
   that is already taking share. Cite the trajectory, not just the position.

3. **What is the dollar impact on *this company* if it plays out?** Translate the
   competitive force into revenue, margin, or FCF impact on the subject. "Cloud-native
   architectures could lower barriers" becomes "if a cloud-native entrant captured 10%
   of the addressable NG9-1-1 market over 5 years, that's ~$12M/yr of revenue at risk
   for Allerium, or ~5% of current revenue." Now the reader can weigh it. A risk you
   can't size is a risk you haven't understood.

### Applying this to strengths and moats

The same discipline applies to the bull case. "Strong installed base" is a label;
"4,200 PSAPs on the platform with an average contract life of 7 years and a historical
churn rate below 3%" is a moat you can underwrite. "Switching costs are high" is an
assertion; "the Kentucky statewide migration took 8 months of planning and 4 months of
execution for 12 PSAPs, and the state has 120 total" tells you *how* high.

When you can't find the number, say so - mark it [A] and flag it as a gap the reader
should investigate. An honest "I couldn't quantify this" is more useful than a
confident-sounding assertion that melts under scrutiny.

### Applying this to risks and threats

Every risk factor in the memo should pass a **"so what" test**: if this risk
materializes, what happens to revenue, margins, or FCF - and over what timeframe?
A risk without an impact estimate is a worry, not an analysis. The pre-mortem
(phase 6) is where you stress-test the risks against the thesis; the competitive
section is where you *size* them so the pre-mortem has something to work with.

Examples of the shift from listing to quantifying:

| Listing (weak) | Quantifying (strong) |
| :-- | :-- |
| "Competition from larger players" | "Competitor X's revenue in the segment grew 14% YoY to ~$X00M; their new platform has been deployed in N states, directly overlapping with the subject's TAM" |
| "Technology disruption risk" | "Cloud-native entrants have raised $X00M in VC funding and signed pilot contracts with N customers; at current adoption rates, they could reach ~5% market penetration by 2028" |
| "Customer concentration" | "Top customer is ~25% of segment revenue (~$56M); the contract runs through 2029, but loss at renewal would cut segment EBITDA by ~$15M" |
| "High switching costs" | "A statewide migration took 8 months planning + 4 months execution for 12 of 120 sites; full cutover expected to take 3+ years, creating de facto lock-in" |
