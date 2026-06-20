"""Fetch a single SEC filing (or one section / attachment) as Markdown.

Writes into the cache (``<cache>/<TICKER>/<FORM>_<DATE>_<ACCESSION>[__<suffix>].md``)
and prints the absolute path(s) to stdout. The script owns the filename so the
result is deterministic and re-discoverable; run with ``--help`` for all flags.
"""

import argparse
import sys

import _common as c


def _attachment_filename(stem: str, document: str, fallback: str) -> str:
    name = c.safe_component(document or fallback)
    return f"{stem}__{name if name.endswith('.md') else name + '.md'}"


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ticker", required=True, help="Ticker, CIK, or company name.")
    p.add_argument(
        "--form", required=True, help="Form type, e.g. 10-K, 10-Q, 8-K, 20-F, 40-F, 6-K, DEF 14A."
    )
    p.add_argument("--year", type=int, help="Calendar year of the filing.")
    p.add_argument("--quarter", type=int, choices=[1, 2, 3, 4], help="Calendar quarter.")
    p.add_argument(
        "--date",
        help="Target a specific filing date (YYYY-MM-DD). "
        "Picks the filing whose filing_date matches exactly, or the "
        "most recent filing on or before that date.",
    )
    p.add_argument(
        "--section",
        help='Extract one item by its SEC code, e.g. "Item 1A" '
        '(10-K/8-K/20-F) or "Part II, Item 1A" (10-Q). Pass "list" '
        "to print the item codes this filing actually contains.",
    )
    p.add_argument(
        "--attachment",
        help='Attachment selector: "list" (print available), "all", an '
        "integer index, or a substring of the document/description "
        '(e.g. "ex-99.1").',
    )
    c.add_identity_arg(p)
    c.add_cache_arg(p)
    args = p.parse_args()

    c.resolve_identity(args.identity)
    company = c.resolve_company(args.ticker)

    # amendments=False: the edgartools API natively excludes amended forms
    # (10-K/A, 10-Q/A, etc.) when this is set. Amendments typically contain
    # only the amended items (e.g. Part III), not the full filing, so picking
    # one silently instead of the original loses most of the content. This
    # matches guide_financials.md's amendments=False recommendation.
    kwargs = {"form": args.form, "amendments": False}
    if args.year:
        kwargs["year"] = args.year
    if args.quarter:
        kwargs["quarter"] = args.quarter
    try:
        filings = list(company.get_filings(**kwargs))
    except Exception as exc:
        c.log(f"ERROR: failed to list {args.form} filings: {exc}")
        sys.exit(1)
    if not filings:
        c.log(
            f"ERROR: no {args.form} filings for {args.ticker} "
            f"(year={args.year}, quarter={args.quarter})."
        )
        sys.exit(1)

    filings.sort(key=lambda f: f.filing_date, reverse=True)

    # --date: pick the filing whose date matches exactly, or the most recent
    # filing on or before the given date.  Useful for targeting a specific
    # 8-K filed today without knowing its accession number.
    if args.date:
        from datetime import date as _date

        try:
            _date.fromisoformat(args.date)
        except ValueError:
            c.log(f"ERROR: --date must be YYYY-MM-DD, got '{args.date}'.")
            sys.exit(1)
        candidates = [f for f in filings if str(getattr(f, "filing_date", "")) <= args.date]
        if not candidates:
            c.log(f"ERROR: no {args.form} filings for {args.ticker} on or before {args.date}.")
            sys.exit(1)
        # candidates is already sorted newest-first; pick the closest one.
        filing = candidates[0]
        c.log(f"--date {args.date}: selected filing dated {filing.filing_date}.")
    else:
        filing = filings[0]

    c.log(f"Resolved {filing.form} filed {filing.filing_date} (accession {filing.accession_no}).")

    out_dir = c.company_dir(c.cache_root(args.cache_dir), company, ticker_hint=args.ticker)
    stem = c.filing_stem(filing)

    if args.attachment:
        attachments = list(filing.attachments)
        if not attachments:
            c.log("ERROR: this filing has no attachments/exhibits.")
            sys.exit(1)

        selector = args.attachment.lower()
        if selector == "list":
            c.log(f"{len(attachments)} attachment(s): index\tdocument\tdescription")
            for i, att in enumerate(attachments):
                print(
                    f"{i}\t{getattr(att, 'document', '') or ''}"
                    f"\t{getattr(att, 'description', '') or ''}"
                )
            return

        if selector == "all":
            saved = []
            for i, att in enumerate(attachments):
                try:
                    fname = _attachment_filename(
                        stem, getattr(att, "document", ""), f"attachment_{i}"
                    )
                    saved.append(c.write_text(out_dir / fname, att.markdown()))
                    c.log(f"  saved {fname}")
                except Exception as exc:
                    c.log(f"  WARNING: attachment {i} failed: {exc}")
            if not saved:
                c.log("ERROR: no attachments could be converted.")
                sys.exit(1)
            for path in saved:
                c.emit(path)
            return

        selected = None
        if args.attachment.isdigit():
            idx = int(args.attachment)
            if not 0 <= idx < len(attachments):
                c.log(f"ERROR: attachment index {idx} out of range (0-{len(attachments) - 1}).")
                sys.exit(1)
            selected = attachments[idx]
        else:
            needle = selector
            for att in attachments:
                doc = (getattr(att, "document", "") or "").lower()
                desc = (getattr(att, "description", "") or "").lower()
                if needle in doc or needle in desc:
                    selected = att
                    break
        if selected is None:
            c.log(f"ERROR: no attachment matched '{args.attachment}'.")
            sys.exit(1)

        content = selected.markdown()
        if not content:
            c.log("ERROR: selected attachment produced no text.")
            sys.exit(1)
        fname = _attachment_filename(stem, getattr(selected, "document", ""), "attachment")
        c.emit(c.write_text(out_dir / fname, content))
        return

    if args.section:
        # Sections are addressed through the parsed data object, not markdown():
        # Filing.markdown() takes no section argument, so passing one there is
        # silently ignored and returns the whole filing. obj()[code] slices it.
        try:
            obj = filing.obj()
        except Exception as exc:
            c.log(
                f"ERROR: could not parse {filing.form} into a structured object "
                f"to address by item: {exc}"
            )
            sys.exit(1)
        items = list(getattr(obj, "items", None) or [])
        addressable = bool(items) and hasattr(obj, "__getitem__")

        if args.section.strip().lower() == "list":
            if not addressable:
                c.log(
                    f"{filing.form} is not item-addressable (it exposes no SEC "
                    f"item codes). Fetch the full filing (omit --section) and map "
                    f"it with list_headings.py."
                )
                return
            c.log(f"{filing.form} contains {len(items)} item(s):")
            for it in items:
                print(it)
            return

        if not addressable:
            c.log(
                f"ERROR: {filing.form} is not item-addressable (no SEC item codes). "
                f"Fetch the full filing (omit --section) and map it with "
                f"list_headings.py, or pull an exhibit with --attachment."
            )
            sys.exit(1)

        content = obj[args.section]
        if content is None or not str(content).strip():
            c.log(
                f"ERROR: item '{args.section}' is not present in this filing. "
                f"Available items: {', '.join(items)}"
            )
            sys.exit(1)
        suffix = c.safe_component(args.section).lower()
        c.emit(c.write_text(out_dir / f"{stem}__{suffix}.md", str(content)))
        return

    content = filing.markdown()
    if not content:
        c.log("ERROR: filing produced no markdown (it may be exhibit-only; try --attachment list).")
        sys.exit(1)
    c.emit(c.write_text(out_dir / f"{stem}.md", content))


if __name__ == "__main__":
    main()
