"""Keyword / theme discovery via EDGAR EFTS full-text search.

Searches the actual text of SEC filings for a keyword or phrase, deduplicates
by company, filters to the $50M-$10B universe, and enriches with market data.
Goes from a keyword to a list of exposed companies — including non-obvious ones.

Usage:
    python scripts/search_themes.py --keyword "cannabis" --since 2026-01-01
    python scripts/search_themes.py --keyword "tariff" --since 2025-01-01 --until 2026-06-17
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c


def _extract_ticker_from_company(company_str: str) -> str | None:
    """Try to extract ticker from EFTS company string like 'SNDL Inc.  (SNDL)  (CIK ...)'."""
    m = re.search(r'\(([A-Z]{1,5})\)', company_str)
    if m:
        return m.group(1)
    return None


def _resolve_ticker_for_cik(cik: str) -> str | None:
    """Try to resolve a ticker from a CIK via edgartools."""
    try:
        from edgar import Company
        co = Company(int(cik.lstrip("0")))
        tickers = getattr(co, "tickers", [])
        if tickers:
            return list(tickers)[0]
    except Exception:
        pass
    return None


def search_and_filter(keyword: str, since: str, until: str, limit: int,
                      cache: Path, mcap_data: dict) -> tuple[list[dict], int]:
    """Search EFTS, deduplicate, filter to universe, enrich.

    Returns (enriched_results, total_unique_before_filter).
    """
    import edgar

    c.log(f"Searching EFTS for '{keyword}' ({since} to {until}, limit={limit})...")

    # EFTS search — both start_date AND end_date must be provided together
    try:
        results = edgar.search_filings(keyword, start_date=since, end_date=until, limit=min(limit, 100))
    except Exception as exc:
        c.log(f"ERROR: EFTS search failed: {exc}")
        return [], 0

    total_server = getattr(results, "total", "?")
    c.log(f"  Server reports {total_server} total matches")

    # Fetch more if needed
    fetched = len(list(results)) if results else 0
    if fetched < limit and fetched > 0:
        try:
            remaining = limit - fetched
            results.fetch_more(remaining)
            c.log(f"  Fetched {remaining} more results")
        except Exception as exc:
            c.log(f"  WARNING: fetch_more failed: {exc}")

    # Deduplicate by CIK -> collect mention counts and most recent filing
    companies: dict[str, dict] = {}  # cik -> {company, cik, mentions, forms, latest_date, latest_form}
    for r in results:
        cik = str(getattr(r, "cik", "")).lstrip("0")
        if not cik:
            continue

        company_name = getattr(r, "company", "Unknown")
        form = getattr(r, "form", "")
        filed = str(getattr(r, "filed", ""))

        if cik not in companies:
            companies[cik] = {
                "cik": cik,
                "company_raw": company_name,
                "mentions": 0,
                "forms": set(),
                "latest_date": "",
                "latest_form": "",
            }

        entry = companies[cik]
        entry["mentions"] += 1
        entry["forms"].add(form)
        if filed > entry["latest_date"]:
            entry["latest_date"] = filed
            entry["latest_form"] = form

    total_unique = len(companies)
    c.log(f"  {total_unique} unique companies found")

    # Resolve tickers and filter by market cap
    enriched = []
    for i, (cik, info) in enumerate(companies.items()):
        if i % 20 == 0:
            c.log(f"  Resolving tickers/market caps: {i}/{total_unique}...")

        # Try to extract ticker from company string first
        ticker = _extract_ticker_from_company(info["company_raw"])
        if not ticker:
            ticker = _resolve_ticker_for_cik(cik)

        if not ticker:
            continue

        ticker = ticker.upper()
        mcap = c.get_market_cap(ticker, mcap_data)
        if not c.in_universe(mcap):
            continue

        # Enrich with yfinance data
        import yfinance as yf
        try:
            yf_info = yf.Ticker(ticker).info or {}
        except Exception:
            yf_info = {}

        enriched.append({
            "ticker": ticker,
            "company": yf_info.get("shortName") or yf_info.get("longName") or info["company_raw"],
            "sector": yf_info.get("sector", "n/a"),
            "industry": yf_info.get("industry", "n/a"),
            "mcap": mcap,
            "price": yf_info.get("currentPrice"),
            "mentions": info["mentions"],
            "latest_date": info["latest_date"],
            "latest_form": info["latest_form"],
        })

    # Sort by most recent filing date (recency-first)
    enriched.sort(key=lambda x: x["latest_date"], reverse=True)
    return enriched, total_unique


def _render_markdown(keyword: str, since: str, until: str,
                     results: list[dict], total_unique: int) -> str:
    """Render theme search results as Markdown."""
    lines = []
    lines.append(f'# Theme Search: "{keyword}" (since {since})\n')
    lines.append(
        f"Found {total_unique} unique companies mentioning \"{keyword}\" in SEC filings.\n"
        f"After universe filter ($50M–$10B): **{len(results)} companies**.\n"
    )

    if not results:
        lines.append("No companies in the $50M–$10B universe matched this search.\n")
        return "\n".join(lines)

    lines.append("| # | Ticker | Company | Sector | Mkt Cap | Price | Mentions | Most Recent Filing |")
    lines.append("|---|--------|---------|--------|---------|-------|----------|--------------------|")
    for i, r in enumerate(results, 1):
        price_s = f"${r['price']:.2f}" if r.get("price") else "n/a"
        lines.append(
            f"| {i} | {r['ticker']} | {r['company']} | {r['sector']} | "
            f"{c.fmt_mcap(r['mcap'])} | {price_s} | {r['mentions']} | "
            f"{r['latest_form']} {r['latest_date']} |"
        )

    lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Keyword/theme discovery via EDGAR EFTS.")
    p.add_argument("--keyword", required=True, help="Search term.")
    p.add_argument("--since", required=True, help="Start date YYYY-MM-DD.")
    p.add_argument("--until", help="End date YYYY-MM-DD (default: today).")
    p.add_argument("--limit", type=int, default=200,
                   help="Max EFTS results to fetch before dedup (default: 200).")
    c.add_identity_arg(p)
    c.add_cache_arg(p)
    args = p.parse_args()

    c.resolve_identity(args.identity)
    cache = c.cache_root(args.cache_dir)
    until = args.until or datetime.now().strftime("%Y-%m-%d")

    mcap_data = c.load_mcap_cache(cache)

    try:
        results, total_unique = search_and_filter(
            args.keyword, args.since, until, args.limit, cache, mcap_data
        )
    finally:
        c.save_mcap_cache(cache, mcap_data)

    c.log(f"Final: {len(results)} companies in universe")

    md = _render_markdown(args.keyword, args.since, until, results, total_unique)

    # Slug: sanitize keyword for filename
    slug_kw = re.sub(r'[^a-zA-Z0-9]+', '-', args.keyword).strip('-').lower()
    slug = f"{slug_kw}_since-{args.since}"
    c.write_output(cache, "themes", slug, md)


if __name__ == "__main__":
    main()
