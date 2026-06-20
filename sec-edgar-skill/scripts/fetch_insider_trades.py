"""Fetch insider transactions (Form 3/4/5) for a single company.

Pulls Form 4 filings for a ticker within a date range and extracts open-market
purchases (code P), sales (code S), option exercises (code M), and tax
withholdings (code F). Writes a Markdown summary into the cache and emits
the path to stdout.

This is a **per-company** tool for due-diligence — "what are insiders of
company X doing?" — not a market-wide scanner. For broad market scanning
of insider clusters and rip/dip buys, see signal-sweep's scan_insiders.py.

Usage:
    # Last 12 months (default)
    python scripts/fetch_insider_trades.py --ticker AAPL

    # Custom date range
    python scripts/fetch_insider_trades.py --ticker AAPL --start 2025-01-01 --end 2026-06-17

    # Only open-market purchases
    python scripts/fetch_insider_trades.py --ticker AAPL --start 2025-06-01 --buys-only

Output is written to ``<cache>/<TICKER>/insider-trades_<START>_<END>.md``
(or ``insider-buys_...`` with --buys-only). The absolute path is emitted to
stdout; progress goes to stderr.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c

# Transaction code labels
_CODE_LABELS = {
    "P": "Purchase",
    "S": "Sale",
    "M": "Option Exercise",
    "F": "Tax Withholding",
    "A": "Award/Grant",
    "G": "Gift",
    "D": "Disposition (non-sale)",
    "C": "Conversion",
    "J": "Other",
}


def _code_label(code: str) -> str:
    return _CODE_LABELS.get(code, code or "Unknown")


def _fmt_shares(s) -> str:
    if s is None:
        return "n/a"
    s = float(s)
    if abs(s) >= 1_000_000:
        return f"{s / 1_000_000:,.2f}M"
    if abs(s) >= 1_000:
        return f"{s / 1_000:,.1f}K"
    return f"{s:,.0f}"


def _fmt_price(p) -> str:
    if p is None or p == 0:
        return "n/a"
    return f"${float(p):,.2f}"


def _fmt_value(shares, price) -> str:
    if shares is None or price is None or price == 0:
        return "n/a"
    val = abs(float(shares) * float(price))
    if val >= 1_000_000:
        return f"${val / 1_000_000:,.2f}M"
    if val >= 1_000:
        return f"${val / 1_000:,.1f}K"
    return f"${val:,.0f}"


def _parse_date(s: str) -> date:
    """Parse YYYY-MM-DD into a date object."""
    from datetime import datetime as dt

    return dt.strptime(s, "%Y-%m-%d").date()


def fetch_insider_trades(
    ticker: str, start: date, end: date, buys_only: bool = False
) -> list[dict]:
    """Fetch and parse Form 4 filings for a ticker within [start, end].

    Returns a list of transaction dicts, newest first.
    """
    company = c.resolve_company(ticker)
    date_range = f"{start.isoformat()}:{end.isoformat()}"
    c.log(f"Fetching Form 4 filings for {ticker} ({date_range})...")

    try:
        form4s = company.get_filings(form="4", date=date_range)
    except Exception as exc:
        c.log(f"ERROR: could not fetch Form 4 filings: {exc}")
        return []

    if form4s is None or len(form4s) == 0:
        c.log(f"No Form 4 filings found for {ticker} in {date_range}.")
        return []

    total = len(form4s)
    c.log(f"  Found {total} Form 4 filings in range.")

    transactions = []
    parsed = 0
    errors = 0

    for filing in form4s:
        try:
            obj = filing.obj()
        except Exception:
            errors += 1
            continue

        filing_date = str(getattr(filing, "filing_date", ""))
        insider_name = getattr(obj, "insider_name", None) or "Unknown"
        position = getattr(obj, "position", None) or "Unknown"

        # Get transactions via to_dataframe()
        try:
            txn_df = obj.to_dataframe()
        except Exception:
            errors += 1
            continue

        if txn_df is None or len(txn_df) == 0:
            parsed += 1
            continue

        for _, row in txn_df.iterrows():
            code = row.get("Code", "")
            shares = row.get("Shares", 0)
            price = row.get("Price", 0)
            remaining = row.get("Remaining Shares", None)

            if buys_only and code != "P":
                continue

            transactions.append(
                {
                    "date": filing_date,
                    "insider": str(insider_name),
                    "role": str(position),
                    "code": str(code or ""),
                    "type": _code_label(code),
                    "shares": shares,
                    "price": price,
                    "remaining": remaining,
                    "accession": (
                        getattr(filing, "accession_no", "")
                        or getattr(filing, "accession_number", "")
                    ),
                }
            )

        parsed += 1
        if parsed % 25 == 0:
            c.log(f"  Parsed {parsed}/{total} filings...")

    if errors > 0:
        c.log(f"  ({errors} filings could not be parsed)")

    c.log(f"  Parsed {parsed} Form 4 filings, found {len(transactions)} transactions.")
    return transactions


def _build_markdown(
    ticker: str, transactions: list[dict], start: date, end: date, buys_only: bool
) -> str:
    """Build a Markdown summary of insider transactions."""
    lines = []
    lines.append(f"# Insider Transactions: {ticker}")
    lines.append("")
    lines.append(f"- **Period:** {start.isoformat()} to {end.isoformat()}")
    lines.append("")

    if not transactions:
        lines.append("No insider transactions found in this period.")
        return "\n".join(lines)

    # --- Aggregate stats ---
    buys = [t for t in transactions if t["code"] == "P"]
    sells = [t for t in transactions if t["code"] == "S"]
    exercises = [t for t in transactions if t["code"] == "M"]

    buy_value = sum(
        abs(t["shares"] * (t["price"] or 0)) for t in buys if t["shares"] and t["price"]
    )
    sell_value = sum(
        abs(t["shares"] * (t["price"] or 0)) for t in sells if t["shares"] and t["price"]
    )

    unique_buyers = set(t["insider"] for t in buys)
    unique_sellers = set(t["insider"] for t in sells)

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Open-market purchases | {len(buys)} |")
    lines.append(f"| Unique buyers | {len(unique_buyers)} |")
    lines.append(f"| Total buy value | {_fmt_value(1, buy_value) if buy_value else 'n/a'} |")
    if not buys_only:
        lines.append(f"| Open-market sales | {len(sells)} |")
        lines.append(f"| Unique sellers | {len(unique_sellers)} |")
        lines.append(f"| Total sell value | {_fmt_value(1, sell_value) if sell_value else 'n/a'} |")
        lines.append(f"| Option exercises | {len(exercises)} |")
        ratio = "n/a"
        if sell_value > 0:
            ratio = f"{buy_value / sell_value:.2f}x"
        elif buy_value > 0:
            ratio = "∞ (no sales)"
        lines.append(f"| Buy/sell ratio (by $) | {ratio} |")
    lines.append("")

    # --- Transaction detail table ---
    label = "Open-Market Purchases" if buys_only else "All Transactions"
    lines.append(f"## {label}")
    lines.append("")
    lines.append("| Date | Insider | Role | Type | Shares | Price | Value | Remaining |")
    lines.append("|------|---------|------|------|--------|-------|-------|-----------|")

    for t in transactions:
        lines.append(
            f"| {t['date']} | {t['insider']} | {t['role']} "
            f"| {t['type']} | {_fmt_shares(t['shares'])} "
            f"| {_fmt_price(t['price'])} "
            f"| {_fmt_value(t['shares'], t['price'])} "
            f"| {_fmt_shares(t['remaining'])} |"
        )

    lines.append("")

    # --- Insider-level summary (who is buying / selling) ---
    if buys:
        lines.append("## Buyers")
        lines.append("")
        lines.append("| Insider | Role | Purchases | Total Shares | Total Value |")
        lines.append("|---------|------|-----------|--------------|-------------|")
        buyer_data: dict[str, dict] = {}
        for t in buys:
            key = t["insider"]
            if key not in buyer_data:
                buyer_data[key] = {"role": t["role"], "count": 0, "shares": 0, "value": 0}
            buyer_data[key]["count"] += 1
            buyer_data[key]["shares"] += abs(t["shares"] or 0)
            buyer_data[key]["value"] += abs((t["shares"] or 0) * (t["price"] or 0))
        for name, d in sorted(buyer_data.items(), key=lambda x: x[1]["value"], reverse=True):
            lines.append(
                f"| {name} | {d['role']} | {d['count']} "
                f"| {_fmt_shares(d['shares'])} "
                f"| {_fmt_value(1, d['value'])} |"
            )
        lines.append("")

    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Fetch insider transactions (Form 4) for a company.")
    p.add_argument("--ticker", required=True, help="Stock ticker to look up.")
    p.add_argument("--start", help="Start date YYYY-MM-DD (default: 12 months ago).")
    p.add_argument("--end", help="End date YYYY-MM-DD (default: today).")
    p.add_argument(
        "--buys-only", action="store_true", help="Show only open-market purchases (code P)."
    )
    c.add_identity_arg(p)
    c.add_cache_arg(p)
    args = p.parse_args()

    c.resolve_identity(args.identity)
    cache = c.cache_root(args.cache_dir)

    end = _parse_date(args.end) if args.end else date.today()
    start = _parse_date(args.start) if args.start else end - timedelta(days=365)

    if start > end:
        c.log("ERROR: --start is after --end.")
        sys.exit(1)

    transactions = fetch_insider_trades(args.ticker, start=start, end=end, buys_only=args.buys_only)

    md = _build_markdown(args.ticker, transactions, start, end, args.buys_only)

    # Write to cache: <cache>/<TICKER>/insider-trades_<START>_<END>.md
    out_dir = c.company_dir(cache, None, ticker_hint=args.ticker)
    prefix = "insider-buys" if args.buys_only else "insider-trades"
    fname = f"{prefix}_{start.isoformat()}_{end.isoformat()}.md"
    path = c.write_text(out_dir / fname, md)
    c.emit(path)


if __name__ == "__main__":
    main()
