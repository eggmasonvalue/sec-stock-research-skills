"""Extract XBRL financial statements from an SEC report (annual or quarterly) to CSV.

Resolves the report (10-K / 20-F / 40-F / 10-Q / 6-K) for the requested year and optional quarter,
parses its XBRL, and writes each statement to
``<cache>/<TICKER>/<FORM>_<DATE>_<ACCESSION>__<statement>.csv``. Prints the
absolute path(s) to stdout. Run ``--help`` for all flags.
"""

import argparse
import sys

import _common as c

# key -> (edgartools accessor on xbrl.statements, output filename suffix)
STATEMENTS = {
    "income": ("income_statement", "income"),
    "balance": ("balance_sheet", "balance"),
    "cashflow": ("cashflow_statement", "cashflow"),  # note: no underscore in "cashflow"
}


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ticker", required=True, help="Ticker, CIK, or company name.")
    p.add_argument("--year", type=int, required=True, help="Calendar year of the report.")
    p.add_argument(
        "--quarter",
        type=int,
        choices=[1, 2, 3, 4],
        help="Calendar quarter of the report (for 10-Q / 6-K).",
    )
    p.add_argument(
        "--form",
        help="Form type, e.g. 10-K, 10-Q, 20-F, 40-F, 6-K. Defaults to 10-Q/6-K if quarter is specified, otherwise annual reports.",
    )
    p.add_argument(
        "--statement",
        choices=["income", "balance", "cashflow", "all"],
        default="all",
        help="Which statement(s) to extract (default: all).",
    )
    c.add_identity_arg(p)
    c.add_cache_arg(p)
    args = p.parse_args()

    c.resolve_identity(args.identity)
    company = c.resolve_company(args.ticker)

    if args.form:
        forms = [args.form]
    elif args.quarter:
        forms = ["10-Q", "6-K"]
    else:
        forms = ["10-K", "20-F", "40-F"]

    c.log(
        f"Finding report ({'/'.join(forms)}) for {args.year}"
        + (f" Q{args.quarter}" if args.quarter else "")
        + " ..."
    )

    kwargs = {"form": forms, "year": args.year, "amendments": False}
    if args.quarter:
        kwargs["quarter"] = args.quarter

    filings = company.get_filings(**kwargs)
    if len(filings) == 0:
        c.log(
            f"No report found for {args.year}"
            + (f" Q{args.quarter}" if args.quarter else "")
            + f" of type {forms}; falling back to most recent."
        )
        kwargs_fallback = {"form": forms, "amendments": False}
        filings = company.get_filings(**kwargs_fallback)
    if len(filings) == 0:
        c.log(f"ERROR: no reports found for {args.ticker} of type {forms}.")
        sys.exit(1)

    filing = None
    xbrl = None
    filing_list = list(filings)
    filing_list.sort(key=lambda f: f.filing_date, reverse=True)

    for f in filing_list:
        try:
            x = f.xbrl()
            if x:
                filing = f
                xbrl = x
                break
        except Exception:
            continue

    if not filing or not xbrl:
        c.log(f"ERROR: no filings with parsed XBRL data found for {args.ticker} in this period.")
        sys.exit(1)

    c.log(
        f"Resolved {filing.form} filed {filing.filing_date} "
        f"(accession {filing.accession_no}) containing XBRL data."
    )

    wanted = ["income", "balance", "cashflow"] if args.statement == "all" else [args.statement]
    out_dir = c.company_dir(c.cache_root(args.cache_dir), company, ticker_hint=args.ticker)
    stem = c.filing_stem(filing)

    saved = []
    for key in wanted:
        accessor, suffix = STATEMENTS[key]
        method = getattr(xbrl.statements, accessor, None)
        if method is None:
            c.log(f"WARNING: {accessor} not available on this filing.")
            continue
        try:
            statement = method()
            if not statement:
                c.log(f"WARNING: no data for {accessor}.")
                continue
            df = statement.to_dataframe()
            path = out_dir / f"{stem}__{suffix}.csv"
            df.to_csv(path, index=True)
            saved.append(path)
            c.log(f"  saved {path.name} ({len(df)} rows)")
        except Exception as exc:
            c.log(f"WARNING: {accessor} failed: {exc}")

    if not saved:
        c.log("ERROR: no statements could be extracted.")
        sys.exit(1)
    for path in saved:
        c.emit(path)


if __name__ == "__main__":
    main()
