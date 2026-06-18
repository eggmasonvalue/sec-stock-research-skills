"""Config-driven market screens via yfinance EquityQuery.

Reads screen definitions from screens.json, injects universe bounds
($50M-$10B, region=us), runs yf.screen(), and optionally enriches the
top results with Ticker.info data.

Usage:
    python scripts/scan_market.py --screen near-52wk-low
    python scripts/scan_market.py --all
    python scripts/scan_market.py --list
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c


def _load_screens(screens_file: Path) -> dict:
    """Load screens.json and return the parsed dict."""
    if not screens_file.exists():
        c.log(f"ERROR: screens file not found: {screens_file}")
        sys.exit(1)
    return json.loads(screens_file.read_text(encoding="utf-8"))


def _build_query(screen: dict, universe: dict):
    """Build a yfinance EquityQuery from screen config + universe bounds."""
    import yfinance as yf

    conditions = [
        yf.EquityQuery("eq", ["region", universe.get("region", "us")]),
        yf.EquityQuery("gte", ["intradaymarketcap", universe.get("market_cap_min", 50_000_000)]),
        yf.EquityQuery("lte", ["intradaymarketcap", universe.get("market_cap_max", 10_000_000_000)]),
    ]

    op_map = {"eq": "eq", "lte": "lte", "gte": "gte", "lt": "lt", "gt": "gt",
              "btwn": "btwn"}

    for f in screen.get("filters", []):
        op = op_map.get(f["op"], f["op"])
        if op == "btwn":
            conditions.append(yf.EquityQuery(op, [f["field"], f["value"][0], f["value"][1]]))
        else:
            conditions.append(yf.EquityQuery(op, [f["field"], f["value"]]))

    return yf.EquityQuery("and", conditions)


def _enrich(quotes: list[dict], size: int) -> list[dict]:
    """Enrich top results with yf.Ticker().info data."""
    import yfinance as yf

    enriched = []
    for i, q in enumerate(quotes[:size]):
        symbol = q.get("symbol", "")
        c.log(f"  Enriching {i+1}/{min(size, len(quotes))}: {symbol}")
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception:
            info = {}

        q["analyst_rating"] = info.get("averageAnalystRating", "n/a")
        q["target_mean"] = info.get("targetMeanPrice")
        q["target_median"] = info.get("targetMedianPrice")
        q["short_pct"] = info.get("shortPercentOfFloat")
        q["insider_pct"] = info.get("heldPercentInsiders")
        q["inst_pct"] = info.get("heldPercentInstitutions")
        q["earnings_growth"] = info.get("earningsQuarterlyGrowth")
        q["revenue_growth"] = info.get("revenueGrowth")
        q["sector"] = info.get("sector", q.get("sector", ""))
        q["industry"] = info.get("industry", q.get("industry", ""))
        q["pe"] = info.get("trailingPE") or info.get("forwardPE")
        q["current_price"] = info.get("currentPrice", q.get("regularMarketPrice"))
        q["market_cap"] = info.get("marketCap", q.get("marketCap"))

        # Trailing 2Y/3Y returns for the "forgotten" screen
        try:
            hist = yf.Ticker(symbol).history(period="3y")
            if hist is not None and len(hist) > 1:
                close = hist["Close"].dropna()
                last = close.iloc[-1]
                import pandas as pd
                last_date = close.index[-1]
                # 2Y return
                prior_2y = close[close.index <= last_date - pd.Timedelta(days=730)]
                if len(prior_2y):
                    q["return_2y"] = (last / prior_2y.iloc[-1] - 1) * 100
                # 3Y return
                prior_3y = close[close.index <= last_date - pd.Timedelta(days=1095)]
                if len(prior_3y):
                    q["return_3y"] = (last / prior_3y.iloc[-1] - 1) * 100
        except Exception:
            pass

        enriched.append(q)

    return enriched


def _fmt_pct(v, mult100=False) -> str:
    if v is None:
        return "n/a"
    val = v * 100 if mult100 else v
    return f"{val:.1f}%"


def _fmt_num(v) -> str:
    if v is None:
        return "n/a"
    return f"{v:.1f}"


def _render_markdown(screen: dict, quotes: list[dict], enriched: bool) -> str:
    """Render screen results as a Markdown table."""
    lines = []
    emoji = screen.get("emoji", "📊")
    name = screen.get("name", screen.get("id", "Screen"))
    lines.append(f"# {emoji} Screen: {name} ({c.universe_label()})\n")
    lines.append(f"_{screen.get('description', '')}_\n")
    lines.append(f"**Results:** {len(quotes)}\n")

    if not quotes:
        lines.append("No results matched this screen.\n")
        return "\n".join(lines)

    if enriched:
        lines.append("| # | Ticker | Company | Price | Mkt Cap | P/E | Short % | Insider % | Inst % | Analyst | Sector |")
        lines.append("|---|--------|---------|-------|---------|-----|---------|-----------|--------|---------|--------|")
        for i, q in enumerate(quotes, 1):
            ticker = q.get("symbol", "?")
            company = q.get("shortName") or q.get("longName") or "?"
            price = q.get("current_price") or q.get("regularMarketPrice")
            price_s = f"${price:.2f}" if price else "n/a"
            mcap_s = c.fmt_mcap(q.get("market_cap"))
            pe_s = _fmt_num(q.get("pe"))
            short_s = _fmt_pct(q.get("short_pct"), mult100=True)
            insider_s = _fmt_pct(q.get("insider_pct"), mult100=True)
            inst_s = _fmt_pct(q.get("inst_pct"), mult100=True)
            analyst = q.get("analyst_rating", "n/a")
            sector = q.get("sector", "n/a")
            lines.append(
                f"| {i} | {ticker} | {company} | {price_s} | {mcap_s} | "
                f"{pe_s} | {short_s} | {insider_s} | {inst_s} | {analyst} | {sector} |"
            )
    else:
        lines.append("| # | Ticker | Company | Price | Mkt Cap |")
        lines.append("|---|--------|---------|-------|---------|")
        for i, q in enumerate(quotes, 1):
            ticker = q.get("symbol", "?")
            company = q.get("shortName") or q.get("longName") or "?"
            price = q.get("regularMarketPrice")
            price_s = f"${price:.2f}" if price else "n/a"
            mcap_s = c.fmt_mcap(q.get("marketCap"))
            lines.append(f"| {i} | {ticker} | {company} | {price_s} | {mcap_s} |")

    lines.append("")
    return "\n".join(lines)


def run_screen(screen: dict, universe: dict, size: int | None, do_enrich: bool, cache: Path) -> str:
    """Run a single screen and return Markdown output."""
    import yfinance as yf

    screen_id = screen.get("id", "unknown")
    screen_size = size or screen.get("size", 25)
    c.log(f"Running screen: {screen_id} (size={screen_size})...")

    query = _build_query(screen, universe)
    sort_field = screen.get("sort", {}).get("field")
    sort_asc = screen.get("sort", {}).get("asc", True)

    try:
        kwargs = {"query": query, "size": screen_size}
        if sort_field:
            kwargs["sortField"] = sort_field
            kwargs["sortAsc"] = sort_asc
        result = yf.screen(**kwargs)
    except Exception as exc:
        c.log(f"  ERROR: screen failed: {exc}")
        return f"# Screen: {screen_id}\n\nError: {exc}\n"

    quotes = result.get("quotes", [])
    c.log(f"  Got {len(quotes)} results (total matching: {result.get('total', '?')})")

    should_enrich = do_enrich and screen.get("enrich", True)
    if should_enrich and quotes:
        quotes = _enrich(quotes, screen_size)

    return _render_markdown(screen, quotes, enriched=should_enrich)


def main():
    p = argparse.ArgumentParser(description="Config-driven market screens.")
    p.add_argument("--screen", help="Screen ID from screens.json.")
    p.add_argument("--all", action="store_true", help="Run all screens.")
    p.add_argument("--list", action="store_true", help="List available screen IDs.")
    p.add_argument("--size", type=int, help="Override the screen's default result size.")
    p.add_argument("--no-enrich", action="store_true", help="Skip enrichment pass.")
    p.add_argument(
        "--screens-file",
        help="Path to screens.json (default: ./screens.json relative to script).",
    )
    c.add_cache_arg(p)
    args = p.parse_args()

    # Resolve screens.json
    if args.screens_file:
        screens_path = Path(args.screens_file)
    else:
        screens_path = Path(__file__).resolve().parent.parent / "screens.json"

    config = _load_screens(screens_path)
    universe = config.get("universe", {})
    screens = config.get("screens", [])
    cache = c.cache_root(args.cache_dir)

    if args.list:
        print("Available screens:\n")
        for s in screens:
            emoji = s.get("emoji", "📊")
            print(f"  {emoji} {s['id']:25s} {s.get('name', '')} — {s.get('description', '')}")
        return

    if not args.screen and not args.all:
        p.error("Specify --screen <id>, --all, or --list.")

    do_enrich = not args.no_enrich
    today = datetime.now().strftime("%Y-%m-%d")

    if args.all:
        all_md = []
        for s in screens:
            md = run_screen(s, universe, args.size, do_enrich, cache)
            all_md.append(md)
        combined = "\n---\n\n".join(all_md)
        slug = f"all-screens_{today}"
        c.write_output(cache, "screens", slug, combined)
    else:
        screen = next((s for s in screens if s["id"] == args.screen), None)
        if not screen:
            available = ", ".join(s["id"] for s in screens)
            c.log(f"ERROR: unknown screen '{args.screen}'. Available: {available}")
            sys.exit(1)
        md = run_screen(screen, universe, args.size, do_enrich, cache)
        slug = f"{args.screen}_{today}"
        c.write_output(cache, "screens", slug, md)


if __name__ == "__main__":
    main()
