"""Two-or-three-stage DCF — forward (assumptions -> intrinsic value) and reverse (price -> implied growth).

Part of the bottom-up-analyst skill's valuation tooling. The judgment — which lens to weight,
how to set the inputs honestly — lives in ``references/guide_valuation.md``; this script just
does the arithmetic the same way every time so memos are comparable. Output is a compact
Markdown summary to stdout. Run ``--help`` for all flags.

Conventions: monetary inputs (``--fcf0``, ``--net-debt``) share one unit (e.g. $millions);
``--shares`` is in the matching count unit (e.g. millions) so per-share output is in dollars.
Rates (``--growth``, ``--terminal-growth``, ``--discount``) are percentages.

Two-stage model (default): FCF grows at ``--growth`` for ``--years``, then a Gordon terminal
value captures perpetual growth at ``--terminal-growth``.

Three-stage model (add ``--growth2`` and ``--years2``): FCF grows at ``--growth`` for
``--years`` (stage 1), then at ``--growth2`` for ``--years2`` (stage 2), then a Gordon
terminal value. Use it whenever the FCF trajectory has a structural bend — the near-term
rate differs materially from the long-run rate. Examples: turnaround cost-out then
normalized growth, hypergrowth investment phase then harvest, cyclical recovery then
trend, regulatory deployment wave then steady-state.

Enterprise value -> less net debt -> equity value -> per share.
"""

import argparse
import sys

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def two_stage_value(fcf0, g1, years, g_term, disc):
    """Return (enterprise_value, pv_stage1, pv_terminal) for a two-stage DCF."""
    if disc <= g_term:
        raise ValueError(
            f"discount rate ({disc:.1%}) must exceed terminal growth ({g_term:.1%}); "
            "the Gordon terminal value is undefined otherwise."
        )
    pv_stage1 = 0.0
    fcf = fcf0
    for t in range(1, years + 1):
        fcf = fcf * (1 + g1)
        pv_stage1 += fcf / (1 + disc) ** t
    fcf_terminal = fcf * (1 + g_term)
    tv = fcf_terminal / (disc - g_term)
    pv_terminal = tv / (1 + disc) ** years
    return pv_stage1 + pv_terminal, pv_stage1, pv_terminal


def three_stage_value(fcf0, g1, years1, g2, years2, g_term, disc):
    """Return (enterprise_value, pv_stage1, pv_stage2, pv_terminal) for a three-stage DCF.

    Stage 1: FCF grows at g1 for years1 (acceleration / inflection).
    Stage 2: FCF grows at g2 for years2 (normalized growth).
    Terminal: Gordon perpetuity at g_term after both stages.
    """
    if disc <= g_term:
        raise ValueError(
            f"discount rate ({disc:.1%}) must exceed terminal growth ({g_term:.1%}); "
            "the Gordon terminal value is undefined otherwise."
        )
    pv_stage1 = 0.0
    fcf = fcf0
    total_years = 0
    for _t in range(1, years1 + 1):
        fcf = fcf * (1 + g1)
        total_years += 1
        pv_stage1 += fcf / (1 + disc) ** total_years
    pv_stage2 = 0.0
    for _t in range(1, years2 + 1):
        fcf = fcf * (1 + g2)
        total_years += 1
        pv_stage2 += fcf / (1 + disc) ** total_years
    fcf_terminal = fcf * (1 + g_term)
    tv = fcf_terminal / (disc - g_term)
    pv_terminal = tv / (1 + disc) ** total_years
    return pv_stage1 + pv_stage2 + pv_terminal, pv_stage1, pv_stage2, pv_terminal


def per_share(fcf0, g1, years, g_term, disc, net_debt, shares, g2=None, years2=None):
    if g2 is not None and years2 is not None:
        ev, _, _, _ = three_stage_value(fcf0, g1, years, g2, years2, g_term, disc)
    else:
        ev, _, _ = two_stage_value(fcf0, g1, years, g_term, disc)
    equity = ev - net_debt
    return equity / shares, ev, equity


def solve_implied_growth(price, fcf0, years, g_term, disc, net_debt, shares):
    """Bisect for the stage-1 growth rate (decimal) that makes IV/share == price."""
    target = price
    lo, hi = -0.95, 5.0

    def f(g):
        v, _, _ = per_share(fcf0, g, years, g_term, disc, net_debt, shares)
        return v - target

    flo, fhi = f(lo), f(hi)
    if flo > 0:
        return None, "below"
    if fhi < 0:
        return None, "above"
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = f(mid)
        if abs(fm) < 1e-9:
            return mid, "ok"
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2, "ok"


def main():
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--mode",
        choices=["forward", "reverse"],
        default="forward",
        help="forward: assumptions -> IV/share. reverse: price -> implied growth.",
    )
    p.add_argument(
        "--fcf0",
        type=float,
        required=True,
        help="Base (normalized) free cash flow, in $M. Use owner earnings.",
    )
    p.add_argument(
        "--growth",
        type=str,
        default="10",
        help="Stage-1 growth %% (forward only). Comma-separated for sensitivity.",
    )
    p.add_argument("--years", type=int, default=10, help="Stage-1 length in years (default 10).")
    p.add_argument(
        "--growth2",
        type=str,
        default=None,
        help="Stage-2 growth %% (three-stage model). Comma-separated for sensitivity. "
        "When set, --years/--growth is stage 1 and --years2/--growth2 is "
        "stage 2, before the terminal value. Use whenever the near-term and "
        "long-run FCF growth rates differ materially.",
    )
    p.add_argument(
        "--years2",
        type=int,
        default=None,
        help="Stage-2 length in years (three-stage model). Required with --growth2.",
    )
    p.add_argument(
        "--terminal-growth",
        type=float,
        default=2.5,
        help="Perpetual growth %% after stage 1 (default 2.5; keep <= long-run GDP).",
    )
    p.add_argument(
        "--discount", type=float, default=10.0, help="Discount rate / WACC %% (default 10)."
    )
    p.add_argument(
        "--shares",
        type=float,
        required=True,
        help="Diluted shares outstanding, same unit as --fcf0 (e.g. millions).",
    )
    p.add_argument(
        "--net-debt",
        type=float,
        default=0.0,
        help="Net debt in $M (total debt - cash & securities). Negative = net cash.",
    )
    p.add_argument(
        "--price",
        type=float,
        default=None,
        help="Current price/share. Required for --mode reverse; optional in forward "
        "to print upside/downside.",
    )
    args = p.parse_args()

    g_term = args.terminal_growth / 100.0
    disc = args.discount / 100.0
    is_three_stage = args.growth2 is not None
    if is_three_stage and args.years2 is None:
        p.error("--years2 is required when --growth2 is set")

    model_label = "three-stage" if is_three_stage else "two-stage"
    print(f"# DCF ({args.mode}) -- {model_label}\n")
    stage_info = f"Stage 1: {args.years}yr"
    if is_three_stage:
        stage_info += f"   Stage 2: {args.years2}yr"
    print(
        f"- Base FCF: {args.fcf0:,.0f}   {stage_info}   "
        f"Terminal growth: {args.terminal_growth:.1f}%   Discount: {args.discount:.1f}%"
    )
    print(
        f"- Shares: {args.shares:,.1f}   Net debt: {args.net_debt:,.0f}"
        + (f"   Price: {args.price:,.2f}" if args.price is not None else "")
    )
    print()

    if args.mode == "reverse":
        if args.price is None:
            p.error("--price is required for --mode reverse")
        g, status = solve_implied_growth(
            args.price, args.fcf0, args.years, g_term, disc, args.net_debt, args.shares
        )
        if status == "above":
            print(
                "**The current price implies growth above 500%/yr for the whole stage** -- "
                "i.e. the price cannot be justified by this model on these cash flows."
            )
        elif status == "below":
            print(
                "**The current price implies a steep perpetual *decline*** -- the market is "
                "pricing the cash flows away."
            )
        else:
            print(f"## Implied stage-1 growth: **{g * 100:.1f}% / yr** for {args.years} years\n")
            print(
                "That is the growth the current price already bakes in. The thesis question: "
                "is that bar too high, about right, or too low versus what this business has "
                "done and can do?"
            )
        return

    # forward
    growths = [float(x) for x in args.growth.split(",") if x.strip() != ""]
    growths2 = (
        [float(x) for x in args.growth2.split(",") if x.strip() != ""] if is_three_stage else [None]
    )

    if is_three_stage:
        print("## Intrinsic value per share (stage-1 growth x stage-2 growth)")
        print()
        header = "| S1 \\\\ S2 |"
        for g2 in growths2:
            header += f" {g2:.0f}% |"
        print(header)
        sep = "| :-- |" + " --: |" * len(growths2)
        print(sep)
        ivs = []
        for g1 in growths:
            row = f"| {g1:.0f}% |"
            for g2 in growths2:
                try:
                    iv, ev, eq = per_share(
                        args.fcf0,
                        g1 / 100.0,
                        args.years,
                        g_term,
                        disc,
                        args.net_debt,
                        args.shares,
                        g2=g2 / 100.0,
                        years2=args.years2,
                    )
                except ValueError as exc:
                    p.error(str(exc))
                ivs.append(iv)
                if args.price is not None:
                    upside = (iv / args.price - 1) * 100
                    row += f" {iv:,.2f} ({upside:+.0f}%) |"
                else:
                    row += f" {iv:,.2f} |"
            print(row)
    else:
        print("## Intrinsic value per share")
        print()
        header = "| Stage-1 growth | IV / share | Enterprise value | Equity value |"
        if args.price is not None:
            header += " Upside vs price |"
        print(header)
        sep = "| :-- | --: | --: | --: |" + (" --: |" if args.price is not None else "")
        print(sep)
        ivs = []
        for g in growths:
            try:
                iv, ev, eq = per_share(
                    args.fcf0, g / 100.0, args.years, g_term, disc, args.net_debt, args.shares
                )
            except ValueError as exc:
                p.error(str(exc))
            ivs.append(iv)
            row = f"| {g:.1f}% | {iv:,.2f} | {ev:,.0f} | {eq:,.0f} |"
            if args.price is not None:
                row += f" {(iv / args.price - 1) * 100:+.1f}% |"
            print(row)

    print()
    if len(ivs) > 1:
        print(
            f"**Intrinsic-value range: {min(ivs):,.2f} -- {max(ivs):,.2f} / share** "
            "(bear--bull across the growth cases above)."
        )
    if args.price is not None:
        _lo, hi = min(ivs), max(ivs)
        mos = (1 - args.price / hi) * 100 if hi > 0 else float("nan")
        print(
            f"\nAt {args.price:,.2f}: margin of safety to the high case is {mos:.0f}%. "
            "Require the thesis to survive the *low* end before you trust it."
        )


if __name__ == "__main__":
    main()
