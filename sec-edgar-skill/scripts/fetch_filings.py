"""Bulk-fetch SEC filings across a year range as Markdown into the cache.

Each filing is written to ``<cache>/<TICKER>/<FORM>_<DATE>_<ACCESSION>.md`` and its
absolute path printed to stdout. With ``--attachments`` each filing's text
attachments are saved alongside it (e.g. a 6-K's Exhibit 99.1). Run ``--help``
for all flags.
"""

import argparse
import sys

import _common as c

_BINARY = (".jpg", ".jpeg", ".png", ".gif", ".zip", ".pdf", ".xlsx", ".xls")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ticker", required=True, help="Ticker, CIK, or company name.")
    p.add_argument("--form", required=True, help="Form type, e.g. 10-Q, 8-K, 6-K.")
    p.add_argument("--start-year", type=int, help="First calendar year (inclusive).")
    p.add_argument("--end-year", type=int, help="Last calendar year (inclusive).")
    p.add_argument(
        "--attachments", action="store_true", help="Also save each filing's text attachments."
    )
    c.add_identity_arg(p)
    c.add_cache_arg(p)
    args = p.parse_args()

    c.resolve_identity(args.identity)
    company = c.resolve_company(args.ticker)

    kwargs = {"form": args.form}
    if args.start_year or args.end_year:
        start = f"{args.start_year}-01-01" if args.start_year else "1994-01-01"
        end = f"{args.end_year}-12-31" if args.end_year else "2100-12-31"
        kwargs["date"] = f"{start}:{end}"
    try:
        filings = list(company.get_filings(**kwargs))
    except Exception as exc:
        c.log(f"ERROR: failed to list {args.form} filings: {exc}")
        sys.exit(1)
    if not filings:
        c.log("No filings matched the criteria.")
        return

    out_dir = c.company_dir(c.cache_root(args.cache_dir), company, ticker_hint=args.ticker)
    c.log(f"Found {len(filings)} {args.form} filing(s) -> {out_dir}")

    saved = []
    for i, filing in enumerate(filings, 1):
        stem = c.filing_stem(filing)
        c.log(f"[{i}/{len(filings)}] {filing.form} {filing.filing_date}")
        try:
            content = filing.markdown()
            if content:
                saved.append(c.write_text(out_dir / f"{stem}.md", content))
            else:
                c.log("  (empty body — likely exhibit-only; use --attachments)")
        except Exception as exc:
            c.log(f"  ERROR main body: {exc}")

        if args.attachments:
            try:
                for j, att in enumerate(list(filing.attachments)):
                    doc = getattr(att, "document", "") or f"attachment_{j}"
                    if doc.lower().endswith(_BINARY):
                        continue
                    try:
                        name = c.safe_component(doc)
                        name = name if name.endswith(".md") else name + ".md"
                        c.write_text(out_dir / f"{stem}__{name}", att.markdown())
                    except Exception:
                        continue
            except Exception as exc:
                c.log(f"  WARNING attachments: {exc}")

    if not saved:
        c.log("ERROR: nothing could be saved.")
        sys.exit(1)
    for path in saved:
        c.emit(path)


if __name__ == "__main__":
    main()
