"""Fetch institutional 13F holder data from 13f.info for a stock or manager.

13f.info is a free, structured interface to SEC 13F filings that provides
pre-parsed, queryable data far more efficiently than parsing raw 13F XML from
EDGAR. It offers three key views:

  **Stock-centric** (who owns this stock?):
    --ticker AAPL             → all institutional holders for the latest quarter
    --ticker AAPL --history   → quarterly holder/share-count summary over time

  **Manager-centric** (what does this fund hold?):
    --manager "Berkshire Hathaway"  → search for a manager, show their holdings
    --cik 0001067983               → look up a manager by CIK directly

  **Cross-reference** (how has a specific manager's position changed?):
    --cik 0000906304 --cusip 205826209  → one manager's history with one stock

All output is written to the cache and the absolute path is emitted to stdout:
  - Stock-centric: ``<cache>/<TICKER>/13f-holders_<YEAR>-Q<Q>.md``
    (or ``13f-history_<TICKER>.md`` for --history)
  - Manager-centric: ``<cache>/managers/13f-manager_<CIK>.md``
  - Cross-reference: ``<cache>/<TICKER>/13f-xref_<CIK>.md``
    (or ``<cache>/managers/13f-xref_<CIK>_<CUSIP>.md`` without --ticker)

Data source: https://13f.info (public, no API key needed).
"""
from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import _common as c  # noqa: F401  (sets UTF-8 stdout, injects truststore)

_BASE = "https://13f.info"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# HTTP / JSON helpers
# ---------------------------------------------------------------------------

def _get_json(url: str) -> dict | list | None:
    """Fetch a JSON endpoint, return parsed data or None on failure."""
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        c.log(f"WARNING: fetch failed for {url}: {exc}")
        return None


def _get_html(url: str) -> str:
    """Fetch an HTML page and return the body as a string."""
    req = Request(url, headers={"User-Agent": _UA, "Accept": "text/html"})
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError) as exc:
        c.log(f"WARNING: fetch failed for {url}: {exc}")
        return ""


# ---------------------------------------------------------------------------
# API endpoints (discovered from 13f.info's client-side code)
# ---------------------------------------------------------------------------
# Working JSON endpoints:
#   /data/autocomplete?q=...              → search managers + CUSIPs
#   /data/cusip/{cusip}/{year}/{quarter}  → all holders for a CUSIP in a quarter
#   /data/manager/{cik}/cusip/{cusip}     → one manager's history with one CUSIP
#
# HTML-only (no JSON API):
#   /cusip/{cusip}                        → stock overview (quarterly summary table)
#   /manager/{cik}-slug                   → manager overview (filing history table)
#   /13f/{filing-slug}                    → single filing holdings table


def _autocomplete(query: str) -> dict | None:
    """Search for managers and CUSIPs by name/ticker."""
    from urllib.parse import quote
    return _get_json(f"{_BASE}/data/autocomplete?q={quote(query)}")


def _holders_for_quarter(cusip: str, year: int, quarter: int) -> dict | None:
    """Get all institutional holders for a CUSIP in a specific quarter."""
    return _get_json(f"{_BASE}/data/cusip/{cusip}/{year}/{quarter}")


def _manager_cusip_history(cik: str, cusip: str) -> dict | None:
    """Get a specific manager's position history for a specific CUSIP."""
    return _get_json(f"{_BASE}/data/manager/{cik}/cusip/{cusip}")


# ---------------------------------------------------------------------------
# Resolve ticker → CUSIP via autocomplete
# ---------------------------------------------------------------------------

def _resolve_cusip(ticker: str) -> tuple[str, str, str] | None:
    """Resolve a ticker to (cusip, symbol, issuer_name) via autocomplete.

    Returns the first equity CUSIP match, or None.
    """
    data = _autocomplete(ticker)
    if not data or not data.get("cusips"):
        return None
    for entry in data["cusips"]:
        name = entry.get("name", "")
        extra = entry.get("extra", "")
        # Format: "AAPL - Apple Inc." / "037833100 - COM"
        parts = name.split(" - ", 1)
        sym = parts[0].strip() if parts else ""
        issuer = parts[1].strip() if len(parts) > 1 else name
        cusip = extra.split(" - ")[0].strip() if " - " in extra else extra.strip()
        if cusip and sym.upper() == ticker.upper():
            return (cusip, sym, issuer)
    # Fallback: return the first CUSIP result
    entry = data["cusips"][0]
    name = entry.get("name", "")
    extra = entry.get("extra", "")
    parts = name.split(" - ", 1)
    sym = parts[0].strip() if parts else ""
    issuer = parts[1].strip() if len(parts) > 1 else name
    cusip = extra.split(" - ")[0].strip() if " - " in extra else extra.strip()
    return (cusip, sym, issuer)


def _resolve_manager(query: str) -> tuple[str, str] | None:
    """Resolve a manager name to (cik, name) via autocomplete.

    Returns the first manager match, or None.
    """
    data = _autocomplete(query)
    if not data or not data.get("managers"):
        return None
    entry = data["managers"][0]
    name = entry.get("name", "")
    url = entry.get("url", "")
    # URL format: /manager/0001067983-berkshire-hathaway-inc
    cik = url.split("/")[-1].split("-")[0] if url else ""
    return (cik, name)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_shares(s: int | float | None) -> str:
    if s is None:
        return "n/a"
    if s >= 1_000_000:
        return f"{s / 1_000_000:,.2f}M"
    if s >= 1_000:
        return f"{s / 1_000:,.1f}K"
    return f"{s:,}"


def _fmt_pct(p: float | None) -> str:
    if p is None:
        return "n/a"
    return f"{p:.1f}%"


# ---------------------------------------------------------------------------
# Output: Stock-centric (who owns this stock?)
# ---------------------------------------------------------------------------

def _build_stock_holders(ticker: str, cusip: str, issuer: str,
                         year: int, quarter: int, top_n: int) -> str | None:
    """Build Markdown for the top institutional holders in a given quarter.

    Returns the Markdown string, or None if no data is available.
    """
    data = _holders_for_quarter(cusip, year, quarter)
    if not data or not data.get("data"):
        c.log(f"No holder data found for {ticker} ({cusip}) Q{quarter} {year}.")
        return None

    holders = data["data"]
    lines = []

    # Determine period end date from the first entry
    period_end = ""
    if holders and isinstance(holders[0][1], list):
        period_end = holders[0][1][0]  # e.g. "2026-03-31"

    lines.append(f"# 13F Institutional Holders: {ticker} ({issuer})")
    lines.append("")
    lines.append(f"- **CUSIP:** {cusip}")
    lines.append(f"- **Period:** Q{quarter} {year}")
    if period_end:
        lines.append(f"- **Holdings as of:** {period_end}")
    lines.append(f"- **Total holders reporting:** {len(holders)}")
    lines.append(f"- **Source:** {_BASE}/cusip/{cusip}/{year}/{quarter}")
    lines.append("")

    # Each holder entry: [[manager_name, cik, cusip], [date, filing_slug], value, shares, principal]
    lines.append(f"## Top {min(top_n, len(holders))} Holders by Shares")
    lines.append("")
    lines.append("| # | Manager | Shares | CIK |")
    lines.append("|---|---------|--------|-----|")

    # Sort by shares descending
    ranked = sorted(holders, key=lambda h: h[3] or 0, reverse=True)

    for i, h in enumerate(ranked[:top_n]):
        manager_info = h[0]
        shares = h[3]

        name = manager_info[0] if isinstance(manager_info, list) else str(manager_info)
        cik = manager_info[1] if isinstance(manager_info, list) and len(manager_info) > 1 else ""

        lines.append(f"| {i+1} | {name} | {_fmt_shares(shares)} | {cik} |")

    if len(holders) > top_n:
        lines.append(f"")
        lines.append(f"*Showing top {top_n} of {len(holders)} holders. "
                     f"Use --top to adjust.*")

    return "\n".join(lines)


def _build_stock_history(ticker: str, cusip: str, issuer: str) -> str | None:
    """Build Markdown for the quarterly holder/share-count history.

    Returns the Markdown string, or None if no data is available.
    This requires scraping the HTML page since there's no JSON endpoint
    for the CUSIP overview.
    """
    import re

    html = _get_html(f"{_BASE}/cusip/{cusip}")
    if not html:
        c.log(f"No history data found for {ticker} ({cusip}).")
        return None

    lines = []
    lines.append(f"# 13F Holder History: {ticker} ({issuer})")
    lines.append("")
    lines.append(f"- **CUSIP:** {cusip}")
    lines.append(f"- **Source:** {_BASE}/cusip/{cusip}")
    lines.append("")

    # Parse the HTML table rows — each row has 5 <td> cells:
    # period (with link), filings, shares, value, options value
    row_pattern = re.compile(
        r'<tr[^>]*>\s*'
        r'<td[^>]*>\s*<a[^>]*>(\d{4}\s+Q\d)</a>\s*</td>\s*'  # period
        r'<td[^>]*>\s*(\d+)\s*</td>\s*'                        # filings
        r'<td[^>]*>\s*([^<]+?)\s*</td>\s*'                     # shares
        r'<td[^>]*>\s*([^<]+?)\s*</td>',                        # value
        re.DOTALL
    )

    lines.append("| Period | Holders | Shares (excl. options) |")
    lines.append("|--------|---------|----------------------|")

    for m in row_pattern.finditer(html):
        period = m.group(1).strip()
        filings = m.group(2).strip()
        shares = m.group(3).strip()
        lines.append(f"| {period} | {filings} | {shares} |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output: Manager-centric (what does this fund hold?)
# ---------------------------------------------------------------------------

def _build_manager_holdings(cik: str, manager_name: str) -> str | None:
    """Build Markdown for a manager's filing history (scraped from HTML).

    Returns the Markdown string, or None if no data is available.
    """
    import re

    # Try to find the manager's page URL via autocomplete
    data = _autocomplete(manager_name)
    manager_url = None
    if data and data.get("managers"):
        for m in data["managers"]:
            url = m.get("url", "")
            if cik in url:
                manager_url = url
                break
        if not manager_url:
            manager_url = data["managers"][0].get("url", "")

    if not manager_url:
        manager_url = f"/manager/{cik}"

    html = _get_html(f"{_BASE}{manager_url}")
    if not html:
        c.log(f"No data found for manager {manager_name} ({cik}).")
        return None

    lines = []
    lines.append(f"# 13F Filings: {manager_name}")
    lines.append("")
    lines.append(f"- **CIK:** {cik}")
    lines.append(f"- **Source:** {_BASE}{manager_url}")
    lines.append("")

    # Parse the filing history table — 7 columns:
    # Quarter (link), Holdings, Value, Top Holdings (title attr), Form Type, Date Filed, Filing ID
    row_pattern = re.compile(
        r'<a[^>]*href="(/13f/[^"]+)"[^>]*>\s*(Q\d\s+\d{4})\s*</a>'
        r'.*?<td[^>]*>\s*(\d+)\s*</td>'                  # holdings
        r'.*?<td[^>]*>\s*([\d,]+)\s*</td>'                # value
        r'.*?<td[^>]*title="([^"]*)"[^>]*>.*?</td>'       # top holdings (title attr)
        r'.*?<td[^>]*title="([^"]*)"[^>]*>.*?</td>'       # form type (title attr)
        r'.*?<td[^>]*>\s*([\d/]+)\s*</td>',               # date filed
        re.DOTALL
    )

    lines.append("| Quarter | Holdings | Top Holdings | Type | Filed |")
    lines.append("|---------|----------|--------------|------|-------|")

    count = 0
    for m in row_pattern.finditer(html):
        quarter = m.group(2).strip()
        holdings = m.group(3).strip()
        top = m.group(5).strip()
        form_type = m.group(6).strip()
        filed = m.group(7).strip()
        lines.append(f"| {quarter} | {holdings} | {top} | {form_type} | {filed} |")
        count += 1
        if count >= 20:
            break

    if count == 0:
        c.log("WARNING: could not parse manager filing history from HTML.")
        return None

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output: Cross-reference (manager × stock history)
# ---------------------------------------------------------------------------

def _build_manager_stock_history(cik: str, cusip: str,
                                  manager_name: str, ticker: str) -> str | None:
    """Build Markdown for a specific manager's position history for a stock.

    Returns the Markdown string, or None if no data is available.
    """
    data = _manager_cusip_history(cik, cusip)
    if not data or not data.get("data"):
        c.log(f"No position history found for {manager_name} in {ticker}.")
        return None

    entries = data["data"]

    lines = []
    lines.append(f"# Position History: {manager_name} → {ticker}")
    lines.append("")
    lines.append(f"- **Manager CIK:** {cik}")
    lines.append(f"- **CUSIP:** {cusip}")
    lines.append(f"- **Source:** {_BASE}/manager/{cik}/cusip/{cusip}")
    lines.append("")

    # Each entry: [[date, filing_slug], value, pct, shares, principal, date_filed, [year, quarter]]
    lines.append("| Period | Shares | % of Portfolio | Filed |")
    lines.append("|--------|--------|---------------|-------|")

    for e in entries:
        pct = e[2]
        shares = e[3]
        date_filed = e[5]
        period_info = e[6]  # [year, quarter]

        period = f"Q{period_info[1]} {period_info[0]}"
        lines.append(f"| {period} | {_fmt_shares(shares)} | {_fmt_pct(pct)} | {date_filed} |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Determine latest quarter
# ---------------------------------------------------------------------------

def _latest_quarter() -> tuple[int, int]:
    """Return the most recent likely 13F quarter with data available.

    13F filings are due 45 days after quarter end, and most large filers
    submit within 45-60 days. We use a 50-day buffer from the *end* of
    the quarter to be safe. Calendar quarters end Mar 31, Jun 30, Sep 30,
    Dec 31.
    """
    from datetime import date, timedelta
    today = date.today()
    # Quarter end dates for the current and previous year
    quarters = []
    for y in [today.year, today.year - 1]:
        quarters.extend([
            (date(y, 3, 31), y, 1),
            (date(y, 6, 30), y, 2),
            (date(y, 9, 30), y, 3),
            (date(y, 12, 31), y, 4),
        ])
    # Sort descending and find the most recent quarter that ended 50+ days ago
    quarters.sort(key=lambda x: x[0], reverse=True)
    for end_date, year, q in quarters:
        if today - end_date >= timedelta(days=50):
            return (year, q)
    # Fallback
    return (today.year - 1, 4)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Fetch 13F institutional holder data from 13f.info."
    )
    # Stock-centric
    p.add_argument("--ticker", help="Stock ticker to look up holders for.")
    p.add_argument("--history", action="store_true",
                   help="Show quarterly holder/share-count history (with --ticker).")
    p.add_argument("--year", type=int, default=None,
                   help="Specific year for holder lookup (default: latest).")
    p.add_argument("--quarter", type=int, default=None, choices=[1, 2, 3, 4],
                   help="Specific quarter (1-4) for holder lookup.")
    p.add_argument("--top", type=int, default=25,
                   help="Number of top holders to show (default: 25).")

    # Manager-centric
    p.add_argument("--manager", help="Manager name to search for.")
    p.add_argument("--cik", help="Manager CIK (10-digit, e.g. 0001067983).")

    # Cross-reference
    p.add_argument("--cusip", help="CUSIP for cross-reference with --cik.")

    c.add_cache_arg(p)
    args = p.parse_args()
    cache = c.cache_root(args.cache_dir)

    # Validate: at least one of --ticker, --manager, or --cik is required
    if not args.ticker and not args.manager and not args.cik:
        p.error("At least one of --ticker, --manager, or --cik is required.")

    # Mode 1: Cross-reference (--cik + --cusip)
    if args.cik and args.cusip:
        manager_name = args.manager or args.cik
        ticker_label = args.ticker or args.cusip
        md = _build_manager_stock_history(args.cik, args.cusip, manager_name, ticker_label)
        if md:
            out_dir = cache / "managers"
            out_dir.mkdir(parents=True, exist_ok=True)
            slug = c.safe_component(args.cik)
            cusip_slug = c.safe_component(args.cusip)
            path = c.write_text(out_dir / f"13f-xref_{slug}_{cusip_slug}.md", md)
            c.emit(path)
        return

    # Mode 2: Stock-centric (--ticker)
    if args.ticker:
        c.log(f"Resolving CUSIP for {args.ticker}...")
        resolved = _resolve_cusip(args.ticker)
        if not resolved:
            c.log(f"ERROR: could not resolve CUSIP for {args.ticker}.")
            sys.exit(1)
        cusip, sym, issuer = resolved
        c.log(f"  {sym} → {issuer} (CUSIP: {cusip})")

        if args.history:
            md = _build_stock_history(args.ticker, cusip, issuer)
            if md:
                out_dir = c.company_dir(cache, None, ticker_hint=args.ticker)
                path = c.write_text(out_dir / f"13f-history_{args.ticker.upper()}.md", md)
                c.emit(path)
            return

        # If --cik is also provided, show cross-reference
        if args.cik:
            manager_name = args.manager or args.cik
            md = _build_manager_stock_history(args.cik, cusip, manager_name, args.ticker)
            if md:
                out_dir = c.company_dir(cache, None, ticker_hint=args.ticker)
                slug = c.safe_component(args.cik)
                path = c.write_text(out_dir / f"13f-xref_{slug}.md", md)
                c.emit(path)
            return

        year = args.year
        quarter = args.quarter
        if not year or not quarter:
            y, q = _latest_quarter()
            year = year or y
            quarter = quarter or q

        c.log(f"Fetching Q{quarter} {year} holders for {sym}...")
        md = _build_stock_holders(args.ticker, cusip, issuer, year, quarter, args.top)
        if md:
            out_dir = c.company_dir(cache, None, ticker_hint=args.ticker)
            path = c.write_text(out_dir / f"13f-holders_{year}-Q{quarter}.md", md)
            c.emit(path)
        return

    # Mode 3: Manager-centric (--manager or --cik without --cusip)
    if args.manager:
        c.log(f"Searching for manager: {args.manager}")
        resolved = _resolve_manager(args.manager)
        if not resolved:
            c.log(f"ERROR: could not find manager '{args.manager}'.")
            sys.exit(1)
        cik, name = resolved
        c.log(f"  Found: {name} (CIK: {cik})")
        md = _build_manager_holdings(cik, name)
        if md:
            out_dir = cache / "managers"
            out_dir.mkdir(parents=True, exist_ok=True)
            slug = c.safe_component(cik)
            path = c.write_text(out_dir / f"13f-manager_{slug}.md", md)
            c.emit(path)
        return

    if args.cik:
        md = _build_manager_holdings(args.cik, args.cik)
        if md:
            out_dir = cache / "managers"
            out_dir.mkdir(parents=True, exist_ok=True)
            slug = c.safe_component(args.cik)
            path = c.write_text(out_dir / f"13f-manager_{slug}.md", md)
            c.emit(path)
        return


if __name__ == "__main__":
    main()
