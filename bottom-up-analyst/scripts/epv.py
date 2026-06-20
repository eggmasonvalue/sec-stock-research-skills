"""Earnings Power Value (EPV) — the no-growth floor.

Part of the bottom-up-analyst skill's valuation tooling. EPV capitalizes *current normalized*
operating earnings with **zero growth credit**: what is the business worth if it simply earns
what it earns today, forever? It is the conservative anchor in a triangulation — pair it with
``dcf.py`` (which prices in growth) and read the gap between them as "how much of the price is
growth I have to believe in." The reasoning behind the inputs is in
``references/guide_valuation.md``.

Conventions: monetary inputs (``--ebit``, ``--net-debt``, ``--maint-capex``, ``--da``) share one
unit (e.g. $millions); ``--shares`` matches (e.g. millions) so per-share output is in dollars.
``--tax`` and ``--wacc`` are percentages.

EPV (enterprise) = normalized NOPAT / WACC, where NOPAT = adjusted EBIT x (1 - tax).
With the optional Greenwald refinement (``--da`` and ``--maint-capex``), adjusted EBIT adds back
the portion of depreciation that exceeds true maintenance capex — earnings the accounting hides.
"""

import argparse
import sys

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--ebit",
        type=float,
        required=True,
        help="Normalized operating earnings (EBIT) in $M. For cyclicals use "
        "mid-cycle EBIT, not the latest year.",
    )
    p.add_argument("--tax", type=float, default=21.0, help="Cash tax rate %% (default 21).")
    p.add_argument(
        "--wacc", type=float, required=True, help="Cost of capital %% used to capitalize earnings."
    )
    p.add_argument(
        "--shares",
        type=float,
        required=True,
        help="Diluted shares, same unit as --ebit (e.g. millions).",
    )
    p.add_argument(
        "--net-debt", type=float, default=0.0, help="Net debt in $M (negative = net cash)."
    )
    p.add_argument(
        "--da",
        type=float,
        default=None,
        help="Depreciation & amortization in $M (optional, for the maintenance-capex "
        "refinement; use with --maint-capex).",
    )
    p.add_argument(
        "--maint-capex",
        type=float,
        default=None,
        help="Maintenance capex in $M (optional). If D&A exceeds it, the excess is "
        "added back to EBIT as hidden earning power.",
    )
    p.add_argument(
        "--price",
        type=float,
        default=None,
        help="Current price/share (optional) to print EPV vs price.",
    )
    args = p.parse_args()

    if args.wacc <= 0:
        p.error("--wacc must be positive")

    tax = args.tax / 100.0
    wacc = args.wacc / 100.0

    adj_ebit = args.ebit
    note = ""
    if args.da is not None and args.maint_capex is not None:
        excess = args.da - args.maint_capex
        adj_ebit = args.ebit + excess
        note = (
            f" (adjusted from {args.ebit:,.0f} by D&A {args.da:,.0f} − maint capex "
            f"{args.maint_capex:,.0f} = {excess:+,.0f})"
        )

    nopat = adj_ebit * (1 - tax)
    epv_enterprise = nopat / wacc
    epv_equity = epv_enterprise - args.net_debt
    epv_share = epv_equity / args.shares

    print("# Earnings Power Value — no-growth floor\n")
    print(f"- Adjusted EBIT: {adj_ebit:,.0f}{note}")
    print(f"- NOPAT (after {args.tax:.0f}% tax): {nopat:,.0f}")
    print(f"- Capitalized at WACC {args.wacc:.1f}%  ->  EPV enterprise: {epv_enterprise:,.0f}")
    print(f"- Less net debt {args.net_debt:,.0f}  ->  EPV equity: {epv_equity:,.0f}")
    print(f"\n## EPV / share (no growth): **{epv_share:,.2f}**")
    if args.price is not None:
        gap = (args.price / epv_share - 1) * 100 if epv_share > 0 else float("nan")
        print(
            f"\nAt {args.price:,.2f}/share, the market pays **{gap:+.0f}%** versus the "
            "no-growth value. That premium is what you are paying for growth and "
            "improvement — decide whether the business can deliver it. A price *below* EPV "
            "means the market assigns the growth (and maybe some of the base) negative value."
        )


if __name__ == "__main__":
    main()
