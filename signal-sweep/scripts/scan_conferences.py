"""Discover companies presenting at conferences via 8-K Item 8.01 filings.

8-K Item 8.01 ("Other Events") is a catch-all that includes conference
announcements among other disclosures. This script searches for 8-K Item 8.01
filings in a date range, filters to the $50M-$10B universe, and text-matches
for conference-related keywords.

Usage:
    python scripts/scan_conferences.py --start 2026-06-16 --end 2026-06-20
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c

# Keywords that suggest a conference announcement
_CONF_KEYWORDS = [
    "conference", "presentation", "investor day", "fireside chat",
    "summit", "symposium", "investor meeting", "analyst day",
    "industry event", "presenting at", "will present",
]
_CONF_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in _CONF_KEYWORDS),
    re.IGNORECASE,
)


def _extract_conference_name(text: str) -> str | None:
    """Try to extract a conference name from filing text."""
    # Common patterns: "at the XYZ Conference", "XYZ Summit", "XYZ Investor Day"
    patterns = [
        r'(?:at|the)\s+(.{10,80}(?:Conference|Summit|Symposium|Forum|Investor Day|Analyst Day))',
        r'(?:presenting at|will present at|participate in)\s+(?:the\s+)?(.{10,80})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            # Clean up trailing punctuation
            name = re.sub(r'[.,;:]+$', '', name).strip()
            if len(name) > 10:
                return name[:100]
    return None


def scan_conferences(start: str, end: str, cache: Path, mcap_data: dict) -> list[dict]:
    """Scan 8-K Item 8.01 filings for conference announcements."""
    import edgar

    c.log(f"Searching 8-K Item 8.01 filings from {start} to {end}...")

    try:
        results = edgar.search_filings(
            forms="8-K", items="8.01",
            start_date=start, end_date=end, limit=100,
        )
    except Exception as exc:
        c.log(f"ERROR: EFTS search failed: {exc}")
        return []

    if results is None:
        c.log("No 8-K Item 8.01 filings found.")
        return []

    total = getattr(results, "total", "?")
    c.log(f"  Found {total} 8-K Item 8.01 filings")

    # Try to fetch more
    try:
        results.fetch_more(200)
    except Exception:
        pass

    conferences = []
    checked = 0
    for r in results:
        checked += 1
        cik = str(getattr(r, "cik", "")).lstrip("0")
        company_raw = getattr(r, "company", "Unknown")
        filed = str(getattr(r, "filed", ""))

        # Try to get ticker
        ticker = None
        m = re.search(r'\(([A-Z]{1,5})\)', company_raw)
        if m:
            ticker = m.group(1)
        if not ticker:
            try:
                from edgar import Company
                co = Company(int(cik))
                tickers = getattr(co, "tickers", [])
                if tickers:
                    ticker = list(tickers)[0]
            except Exception:
                continue

        if not ticker:
            continue

        ticker = ticker.upper()
        mcap = c.get_market_cap(ticker, mcap_data)
        if not c.in_universe(mcap):
            continue

        # Fetch filing text and check for conference keywords
        try:
            accession = getattr(r, "accession_number", "") or getattr(r, "accession_no", "")
            # Try to get filing text from the search result or by fetching
            filing_text = ""
            try:
                # Some EFTS results have a snippet or we can fetch the filing
                filing_text = str(r)
            except Exception:
                pass

            if not filing_text:
                continue

            if not _CONF_PATTERN.search(filing_text):
                # Also try fetching the actual filing for keyword matching
                # if the search result snippet doesn't contain keywords
                continue

        except Exception:
            continue

        conf_name = _extract_conference_name(filing_text)

        import yfinance as yf
        try:
            yf_info = yf.Ticker(ticker).info or {}
        except Exception:
            yf_info = {}

        conferences.append({
            "ticker": ticker,
            "company": yf_info.get("shortName") or yf_info.get("longName") or company_raw,
            "sector": yf_info.get("sector", "n/a"),
            "mcap": mcap,
            "price": yf_info.get("currentPrice"),
            "filed": filed,
            "conference": conf_name or "(conference details in filing)",
        })

        if checked % 20 == 0:
            c.log(f"  Checked {checked} filings...")

    c.log(f"  Checked {checked} filings, found {len(conferences)} conference announcements")
    return conferences


def _render_markdown(start: str, end: str, conferences: list[dict]) -> str:
    """Render conference discovery results as Markdown."""
    lines = []
    lines.append(f"# Conference Discovery ({start} to {end})\n")
    lines.append(
        f"Scanned 8-K Item 8.01 filings for conference-related announcements.\n"
        f"Found **{len(conferences)}** companies in the $50M–$10B universe.\n"
    )

    if not conferences:
        lines.append("No conference announcements found in this date range.\n")
        return "\n".join(lines)

    lines.append("| # | Ticker | Company | Sector | Mkt Cap | Price | Filed | Conference |")
    lines.append("|---|--------|---------|--------|---------|-------|-------|------------|")
    for i, conf in enumerate(conferences, 1):
        price_s = f"${conf['price']:.2f}" if conf.get("price") else "n/a"
        lines.append(
            f"| {i} | {conf['ticker']} | {conf['company']} | {conf['sector']} | "
            f"{c.fmt_mcap(conf['mcap'])} | {price_s} | {conf['filed']} | {conf['conference']} |"
        )

    lines.append("")
    lines.append("_Note: 8-K Item 8.01 is a catch-all — some results may not be conference "
                 "announcements. Review the filings for confirmation._\n")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Conference discovery via 8-K Item 8.01.")
    p.add_argument("--start", required=True, help="Start date YYYY-MM-DD.")
    p.add_argument("--end", required=True, help="End date YYYY-MM-DD.")
    c.add_identity_arg(p)
    c.add_cache_arg(p)
    args = p.parse_args()

    c.resolve_identity(args.identity)
    cache = c.cache_root(args.cache_dir)

    mcap_data = c.load_mcap_cache(cache)

    try:
        conferences = scan_conferences(args.start, args.end, cache, mcap_data)
    finally:
        c.save_mcap_cache(cache, mcap_data)

    md = _render_markdown(args.start, args.end, conferences)
    slug = f"{args.start}_to_{args.end}"
    c.write_output(cache, "conferences", slug, md)

    print(md)


if __name__ == "__main__":
    main()
