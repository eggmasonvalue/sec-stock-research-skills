"""Orient on a company before extracting — the mandatory first step.

Resolves the company, prints its ``.to_context()`` summary, surveys the mix of
forms it has actually filed over a recent window (per-form counts with date
ranges), and lists the most recent filings. Output is compact Markdown to stdout;
run with ``--help`` for all flags.

Run this first for any filings work. It is the cheapest way to see what a company
actually files *now* and how that has changed over time, so you fetch the right
forms instead of assuming a form set from memory. The output is neutral — it shows
the filing history and leaves what is significant to you (or the framework driving
you) to decide.
"""

import argparse
import datetime as _dt
import sys

import _common as c


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ticker", required=True, help="Ticker, CIK, or company name.")
    p.add_argument(
        "--years",
        type=int,
        default=3,
        help="Survey the filing mix over the last N calendar years (default: 3).",
    )
    p.add_argument(
        "--recent", type=int, default=15, help="Also list the N most recent filings (default: 15)."
    )
    c.add_identity_arg(p)
    args = p.parse_args()

    c.resolve_identity(args.identity)
    company = c.resolve_company(args.ticker)

    # 1) Cheap metadata summary.
    print(f"# Orientation: {args.ticker.upper()}\n")
    try:
        print(company.to_context())
    except Exception as exc:
        c.log(f"WARNING: .to_context() unavailable ({exc}); printing basic metadata.")
        print(f"COMPANY: {getattr(company, 'name', 'n/a')}")
        print(f"CIK: {getattr(company, 'cik', 'n/a')}")
        print(f"SIC: {getattr(company, 'sic', 'n/a')}")

    # 2) Filing-mix survey over the window.
    this_year = _dt.date.today().year
    start_year = this_year - max(args.years - 1, 0)
    date_range = f"{start_year}-01-01:{this_year}-12-31"
    try:
        df = company.get_filings(date=date_range).to_pandas()
    except Exception as exc:
        c.log(f"ERROR: could not survey filings for {date_range}: {exc}")
        sys.exit(1)

    print(f"\n## Filing mix {start_year}-{this_year}")
    if df is None or len(df) == 0:
        print("- (no filings in this window; widen --years)")
        return

    df = df.copy()
    df["_date"] = df["filing_date"].astype(str)

    rows = []
    for form, grp in df.groupby("form"):
        d = grp["_date"]
        rows.append((str(form), len(grp), d.min(), d.max()))
    rows.sort(key=lambda r: (r[1], r[3]), reverse=True)

    print("\n| Form | Count | Earliest | Latest |")
    print("| :-- | --: | :-- | :-- |")
    for form, n, lo, hi in rows:
        print(f"| {form} | {n} | {lo} | {hi} |")

    # 3) Most recent filings.
    n_recent = min(args.recent, len(df))
    print(f"\n## {n_recent} most recent filings")
    recent = df.sort_values("_date", ascending=False).head(n_recent)
    print("\n| Date | Form | Accession |")
    print("| :-- | :-- | :-- |")
    for _, row in recent.iterrows():
        print(f"| {row['_date']} | {row['form']} | {row.get('accession_number', '')} |")


if __name__ == "__main__":
    main()
