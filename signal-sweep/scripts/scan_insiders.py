"""Scan Form 4 insider purchases for cluster buys, rip/dip buys, and 13D filings.

Pulls the daily Form 4 bulk index over a rolling lookback window, filters to
the $50M-$10B universe, parses open-market purchases (code P only), and
detects:
  - Cluster buys: 2+ distinct insiders buying the same stock within the window
  - Rip buys: insider buys after an unusually large rally (z-score based)
  - Dip buys: insider buys into an unusually large decline (z-score based)

Rip/dip detection is volatility-adjusted — a 20% move means nothing for a
biotech that swings 20% monthly, but it's exceptional for a utility. The
trailing 30-day return is measured against the stock's own historical
volatility (annualized stdev of daily returns over the prior year, scaled to
a 30-day window). A z-score beyond the threshold (default ±1.5) flags the
purchase.

Also pulls SC 13D / 13D/A filings for activist blockholders.

Usage:
    python scripts/scan_insiders.py --date yesterday --lookback 5
    python scripts/scan_insiders.py --date 2026-06-16 --lookback 5 --webhook $DISCORD_WEBHOOK_URL
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trading_dates(end_date: str, lookback: int) -> list[str]:
    """Generate dates to scan (calendar days, skipping weekends)."""
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    d = end
    while len(dates) < lookback:
        if d.weekday() < 5:
            dates.append(d.strftime("%Y-%m-%d"))
        d -= timedelta(days=1)
    return list(reversed(dates))


def _post_discord(webhook_url: str, embeds: list[dict]) -> None:
    """Post embeds to Discord webhook, batching at 10 per request."""
    import requests
    for i in range(0, len(embeds), 10):
        batch = embeds[i:i + 10]
        resp = requests.post(webhook_url, json={"embeds": batch}, timeout=30)
        if resp.status_code not in (200, 204):
            c.log(f"WARNING: Discord webhook returned {resp.status_code}: {resp.text[:200]}")


# ---------------------------------------------------------------------------
# Rip / dip detection
# ---------------------------------------------------------------------------

_TRADING_DAYS_30D = 22  # ~22 trading days in a calendar month


def compute_move_zscore(ticker: str) -> dict | None:
    """Compute the trailing 30-day return z-score for a stock.

    Returns {"return_30d": float, "vol_30d": float, "zscore": float} or None
    if there isn't enough price history.

    The z-score measures how unusual the recent 30-day move is relative to the
    stock's own historical behavior:
      - trailing_return = price now / price 22 trading days ago - 1
      - vol_30d = stdev of daily returns over the prior year, scaled to a
        22-trading-day window (multiply by sqrt(22))
      - zscore = trailing_return / vol_30d
    """
    import yfinance as yf

    try:
        hist = yf.Ticker(ticker).history(period="1y")
        if hist is None or len(hist) < 60:
            return None
        close = hist["Close"].dropna()
        if len(close) < 60:
            return None
    except Exception:
        return None

    daily_returns = close.pct_change().dropna()
    if len(daily_returns) < 40:
        return None

    # Trailing 30-day return
    n = min(_TRADING_DAYS_30D, len(close) - 1)
    trailing_return = close.iloc[-1] / close.iloc[-1 - n] - 1

    # Historical daily stdev, scaled to 30-day window
    daily_std = daily_returns.std()
    if daily_std == 0 or math.isnan(daily_std):
        return None
    vol_30d = daily_std * math.sqrt(n)

    zscore = trailing_return / vol_30d

    return {
        "return_30d": trailing_return,
        "vol_30d": vol_30d,
        "zscore": zscore,
    }


def tag_rip_dip(purchases_by_ticker: dict[str, list[dict]],
                zscore_threshold: float = 1.5) -> None:
    """Tag each purchase with rip/dip signals based on move z-score.

    Mutates purchase dicts in place, adding:
      - "return_30d", "vol_30d", "zscore": the raw numbers
      - "signal": "rip" | "dip" | None
    """
    tickers = list(purchases_by_ticker.keys())
    c.log(f"Computing move z-scores for {len(tickers)} tickers...")

    for i, ticker in enumerate(tickers):
        if i % 20 == 0 and i > 0:
            c.log(f"  z-scores: {i}/{len(tickers)}...")

        result = compute_move_zscore(ticker)

        for purchase in purchases_by_ticker[ticker]:
            if result is None:
                purchase["return_30d"] = None
                purchase["vol_30d"] = None
                purchase["zscore"] = None
                purchase["signal"] = None
                continue

            purchase["return_30d"] = result["return_30d"]
            purchase["vol_30d"] = result["vol_30d"]
            purchase["zscore"] = result["zscore"]

            z = result["zscore"]
            if z >= zscore_threshold:
                purchase["signal"] = "rip"
            elif z <= -zscore_threshold:
                purchase["signal"] = "dip"
            else:
                purchase["signal"] = None

    c.log(f"  z-scores done.")


# ---------------------------------------------------------------------------
# Form 4 scanning
# ---------------------------------------------------------------------------

def scan_form4s(dates: list[str], cache: Path,
                mcap_data: dict) -> dict[str, list[dict]]:
    """Scan Form 4 filings across dates, return all purchases by ticker.

    Returns {ticker: [purchase_dicts]} — downstream code detects clusters
    and rip/dip from this raw collection.
    """
    import edgar

    purchases_by_ticker: dict[str, list[dict]] = defaultdict(list)
    seen_keys: dict[str, set] = defaultdict(set)

    for date_str in dates:
        c.log(f"Fetching Form 4 index for {date_str}...")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            filings = edgar.get_filings(
                year=dt.year,
                quarter=(dt.month - 1) // 3 + 1,
                form="4",
                filing_date=date_str,
                amendments=False,
            )
        except Exception as exc:
            c.log(f"  WARNING: could not fetch Form 4 index for {date_str}: {exc}")
            continue

        if filings is None:
            c.log(f"  No Form 4 filings found for {date_str}")
            continue

        try:
            df = filings.to_pandas()
        except Exception:
            c.log(f"  WARNING: could not convert filings to DataFrame for {date_str}")
            continue

        c.log(f"  Found {len(df)} Form 4 filings for {date_str}")

        for idx, filing in enumerate(filings):
            if idx >= len(df):
                break

            try:
                obj = filing.obj()
            except Exception:
                continue

            ticker = None
            try:
                issuer = obj.issuer
                ticker = getattr(issuer, "ticker", None)
                if not ticker:
                    ticker = getattr(issuer, "trading_symbol", None)
            except Exception:
                pass

            if not ticker:
                continue
            ticker = ticker.upper().strip()

            mcap = c.get_market_cap(ticker, mcap_data)
            if not c.in_universe(mcap):
                continue

            # Use to_dataframe() to get transactions + remaining shares
            try:
                txn_df = obj.to_dataframe()
            except Exception:
                continue

            if txn_df is None or len(txn_df) == 0:
                continue

            # Filter to open-market purchases (code P)
            p_mask = txn_df["Code"] == "P" if "Code" in txn_df.columns else None
            if p_mask is None:
                continue
            purchases_df = txn_df[p_mask]

            for _, row in purchases_df.iterrows():
                shares = row.get("Shares", 0) or 0
                price = row.get("Price", 0) or 0
                if shares <= 0:
                    continue

                insider_name = row.get("Insider") or getattr(obj, "insider_name", "Unknown")
                position = row.get("Position") or getattr(obj, "position", "Unknown")
                try:
                    company_name = getattr(obj.issuer, "name", ticker)
                except Exception:
                    company_name = ticker

                remaining = row.get("Remaining Shares")
                shares_out = c.get_cached_shares_out(ticker, mcap_data)

                key = f"{insider_name}|{date_str}"
                if key not in seen_keys[ticker]:
                    seen_keys[ticker].add(key)
                    purchases_by_ticker[ticker].append({
                        "insider": insider_name,
                        "role": position,
                        "shares": shares,
                        "price": price,
                        "date": date_str,
                        "company": company_name,
                        "mcap": mcap,
                        "remaining": remaining,
                        "shares_out": shares_out,
                    })

            if idx % 50 == 0 and idx > 0:
                c.log(f"  Parsed {idx}/{len(df)} filings...")

        c.log(f"  Done with {date_str}")

    return dict(purchases_by_ticker)


def detect_clusters(purchases_by_ticker: dict[str, list[dict]]) -> list[dict]:
    """Find cluster buys: 2+ distinct insiders buying the same ticker."""
    clusters = []
    for ticker, buys in purchases_by_ticker.items():
        unique_insiders = set(b["insider"] for b in buys)
        if len(unique_insiders) >= 2:
            # Collect signals present on any purchase in the cluster
            signals = set()
            for b in buys:
                if b.get("signal"):
                    signals.add(b["signal"])

            clusters.append({
                "ticker": ticker,
                "company": buys[0]["company"],
                "mcap": buys[0]["mcap"],
                "insiders": buys,
                "num_insiders": len(unique_insiders),
                "date_range": (f"{min(b['date'] for b in buys)} to "
                               f"{max(b['date'] for b in buys)}"),
                "signals": sorted(signals),
                # Use the first purchase's z-score data (same ticker, same values)
                "return_30d": buys[0].get("return_30d"),
                "zscore": buys[0].get("zscore"),
            })

    clusters.sort(key=lambda x: x["num_insiders"], reverse=True)
    return clusters


def collect_notable_singles(purchases_by_ticker: dict[str, list[dict]],
                            cluster_tickers: set[str]) -> list[dict]:
    """Collect rip/dip-tagged purchases that aren't part of a cluster.

    These are individual insider buys that are notable because of the
    volatility-adjusted price context, even without a second insider
    confirming.
    """
    notable = []
    for ticker, buys in purchases_by_ticker.items():
        if ticker in cluster_tickers:
            continue
        for b in buys:
            if b.get("signal"):
                notable.append({**b, "ticker": ticker})

    # Sort by absolute z-score (most extreme first)
    notable.sort(key=lambda x: abs(x.get("zscore") or 0), reverse=True)
    return notable


# ---------------------------------------------------------------------------
# 13D scanning (unchanged)
# ---------------------------------------------------------------------------

def scan_13d(dates: list[str], cache: Path, mcap_data: dict) -> list[dict]:
    """Scan SC 13D / 13D/A filings for activist blockholders."""
    import edgar

    results = []
    for date_str in dates:
        c.log(f"Fetching 13D/13D-A index for {date_str}...")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            filings = edgar.get_filings(
                year=dt.year,
                quarter=(dt.month - 1) // 3 + 1,
                form=["SC 13D", "SC 13D/A"],
                filing_date=date_str,
            )
        except Exception as exc:
            c.log(f"  WARNING: could not fetch 13D index for {date_str}: {exc}")
            continue

        if filings is None:
            continue

        for filing in filings:
            company = getattr(filing, "company", "Unknown")
            cik = getattr(filing, "cik", "")

            ticker = None
            try:
                from edgar import Company
                co = Company(int(cik))
                tickers = getattr(co, "tickers", [])
                if tickers:
                    ticker = list(tickers)[0]
            except Exception:
                pass

            if not ticker:
                continue

            mcap = c.get_market_cap(ticker, mcap_data)
            if not c.in_universe(mcap):
                continue

            results.append({
                "ticker": ticker.upper(),
                "company": company,
                "mcap": mcap,
                "filer": getattr(filing, "company", "Unknown"),
                "date": date_str,
                "form": getattr(filing, "form", "SC 13D"),
                "accession": (getattr(filing, "accession_no", "")
                              or getattr(filing, "accession_number", "")),
            })

    return results


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------

def _signal_badge(signal: str | None) -> str:
    if signal == "rip":
        return " 🚀"
    if signal == "dip":
        return " 🔻"
    return ""


def _zscore_str(z: float | None) -> str:
    if z is None:
        return "n/a"
    return f"{z:+.1f}σ"


def _return_str(r: float | None) -> str:
    if r is None:
        return "n/a"
    return f"{r * 100:+.1f}%"


def _pct_of_holding(shares: float, remaining: float | None) -> str:
    """Purchase as % of post-transaction holding."""
    if not remaining or remaining <= 0:
        return "n/a"
    return f"{shares / remaining * 100:.1f}%"


def _pct_of_outstanding(shares: float, shares_out: int | None) -> str:
    """Purchase as % of total shares outstanding."""
    if not shares_out or shares_out <= 0:
        return "n/a"
    pct = shares / shares_out * 100
    if pct < 0.01:
        return "<0.01%"
    return f"{pct:.2f}%"


def _build_summary(purchases_by_ticker: dict[str, list[dict]],
                   clusters: list[dict], notable: list[dict],
                   filings_13d: list[dict], mcap_data: dict) -> list[str]:
    """Build a summary header with key stats and sector breakdown."""
    lines = []

    # Aggregate stats
    all_purchases = [b for buys in purchases_by_ticker.values() for b in buys]
    total_purchases = len(all_purchases)
    unique_tickers = len(purchases_by_ticker)
    unique_insiders = len(set(b["insider"] for b in all_purchases))
    total_dollar = sum(b["shares"] * b["price"] for b in all_purchases)
    rip_count = sum(1 for b in all_purchases if b.get("signal") == "rip")
    dip_count = sum(1 for b in all_purchases if b.get("signal") == "dip")

    lines.append("## Summary\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Purchases (code P, $50M\u2013$10B) | {total_purchases} |")
    lines.append(f"| Unique tickers | {unique_tickers} |")
    lines.append(f"| Unique insiders | {unique_insiders} |")
    lines.append(f"| Total dollar volume | ${total_dollar:,.0f} |")
    lines.append(f"| Cluster buys | {len(clusters)} |")
    lines.append(f"| Dip buys (\u2264 -1.5\u03c3) | {dip_count} |")
    lines.append(f"| Rip buys (\u2265 +1.5\u03c3) | {rip_count} |")
    lines.append(f"| 13D filings | {len(filings_13d)} |")
    lines.append("")

    # Largest purchase
    if all_purchases:
        largest = max(all_purchases, key=lambda b: b["shares"] * b["price"])
        lval = largest["shares"] * largest["price"]
        # Find the ticker for this purchase
        lticker = ""
        for t, buys in purchases_by_ticker.items():
            if largest in buys:
                lticker = t
                break
        lines.append(f"**Largest purchase:** {largest['insider']} "
                     f"({largest['role']}) bought ${lval:,.0f} of "
                     f"{lticker} ({largest['company']})\n")

    # Sector breakdown
    sector_counts: dict[str, int] = defaultdict(int)
    sector_dollars: dict[str, float] = defaultdict(float)
    for ticker, buys in purchases_by_ticker.items():
        sector = c.get_cached_sector(ticker, mcap_data)
        sector_counts[sector] += len(buys)
        sector_dollars[sector] += sum(b["shares"] * b["price"] for b in buys)

    if sector_counts:
        # Sort by dollar volume descending
        sorted_sectors = sorted(sector_dollars.items(),
                                key=lambda x: x[1], reverse=True)
        lines.append("### Sector Breakdown\n")
        lines.append("| Sector | Purchases | Dollar Volume |")
        lines.append("|--------|-----------|---------------|")
        for sector, dollars in sorted_sectors:
            count = sector_counts[sector]
            lines.append(f"| {sector} | {count} | ${dollars:,.0f} |")
        lines.append("")

    return lines


def _build_markdown(purchases_by_ticker: dict[str, list[dict]],
                    clusters: list[dict], notable: list[dict],
                    filings_13d: list[dict], dates: list[str],
                    mcap_data: dict) -> str:
    """Build Markdown output from scan results."""
    lines = []
    date_range = f"{dates[0]} to {dates[-1]}" if len(dates) > 1 else dates[0]
    lines.append(f"# Insider Activity Scan ({date_range})\n")

    # Summary header
    lines.extend(_build_summary(purchases_by_ticker, clusters, notable,
                                filings_13d, mcap_data))

    # --- Cluster buys ---
    lines.append(f"## Cluster Buys ({len(clusters)} found)\n")
    if not clusters:
        lines.append("No cluster buys detected in this window.\n")
    else:
        lines.append("A cluster buy = 2+ distinct insiders buying the same stock "
                     "within the window.\n")
        for cl in clusters:
            badges = "".join(_signal_badge(s) for s in cl.get("signals", []))
            lines.append(f"### {cl['ticker']} — {cl['company']}{badges}")
            lines.append(f"- **Market Cap:** {c.fmt_mcap(cl['mcap'])}")
            lines.append(f"- **Insiders buying:** {cl['num_insiders']}")
            lines.append(f"- **Window:** {cl['date_range']}")
            z = cl.get("zscore")
            r = cl.get("return_30d")
            if z is not None:
                lines.append(f"- **30-day move:** {_return_str(r)} "
                             f"({_zscore_str(z)} vs own history)")
            lines.append(f"- **Link:** [Yahoo Finance]"
                         f"(https://finance.yahoo.com/quote/{cl['ticker']})")
            lines.append("")
            lines.append("| Insider | Role | Shares | Price "
                         "| % of Holding | % of O/S | Date |")
            lines.append("|---------|------|--------|-------"
                         "|--------------|----------|------|")
            for ins in cl["insiders"]:
                lines.append(
                    f"| {ins['insider']} | {ins['role']} | "
                    f"{ins['shares']:,.0f} | ${ins['price']:.2f} | "
                    f"{_pct_of_holding(ins['shares'], ins.get('remaining'))} | "
                    f"{_pct_of_outstanding(ins['shares'], ins.get('shares_out'))} | "
                    f"{ins['date']} |"
                )
            lines.append("")

    # --- Notable individual purchases (rip/dip) ---
    if notable:
        rips = [n for n in notable if n.get("signal") == "rip"]
        dips = [n for n in notable if n.get("signal") == "dip"]

        lines.append(f"## Notable Individual Purchases "
                     f"({len(rips)} rip, {len(dips)} dip)\n")
        lines.append("Volatility-adjusted: the 30-day return is measured against "
                     "the stock's own historical volatility. A z-score beyond "
                     "±1.5σ flags the purchase as unusual.\n")

        if dips:
            lines.append("### 🔻 Dip Buys (buying into unusual weakness)\n")
            lines.append("| Ticker | Company | Insider | Role | Shares | Price "
                         "| % of Holding | 30d Move | Z-Score | Mkt Cap |")
            lines.append("|--------|---------|---------|------|--------|-------"
                         "|--------------|---------|---------|---------|")
            for n in dips:
                lines.append(
                    f"| {n['ticker']} | {n['company']} | {n['insider']} | "
                    f"{n['role']} | {n['shares']:,.0f} | ${n['price']:.2f} | "
                    f"{_pct_of_holding(n['shares'], n.get('remaining'))} | "
                    f"{_return_str(n.get('return_30d'))} | "
                    f"{_zscore_str(n.get('zscore'))} | "
                    f"{c.fmt_mcap(n.get('mcap'))} |"
                )
            lines.append("")

        if rips:
            lines.append("### 🚀 Rip Buys (buying into unusual strength)\n")
            lines.append("| Ticker | Company | Insider | Role | Shares | Price "
                         "| % of Holding | 30d Move | Z-Score | Mkt Cap |")
            lines.append("|--------|---------|---------|------|--------|-------"
                         "|--------------|---------|---------|---------|")
            for n in rips:
                lines.append(
                    f"| {n['ticker']} | {n['company']} | {n['insider']} | "
                    f"{n['role']} | {n['shares']:,.0f} | ${n['price']:.2f} | "
                    f"{_pct_of_holding(n['shares'], n.get('remaining'))} | "
                    f"{_return_str(n.get('return_30d'))} | "
                    f"{_zscore_str(n.get('zscore'))} | "
                    f"{c.fmt_mcap(n.get('mcap'))} |"
                )
            lines.append("")

    # --- 13D filings ---
    lines.append(f"## Activist 13D Filings ({len(filings_13d)} found)\n")
    if not filings_13d:
        lines.append("No SC 13D / 13D/A filings in the $50M–$10B universe "
                     "for this window.\n")
    else:
        lines.append("| Ticker | Company | Market Cap | Filer | Date | Form |")
        lines.append("|--------|---------|-----------|-------|------|------|")
        for f13 in filings_13d:
            lines.append(
                f"| {f13['ticker']} | {f13['company']} | "
                f"{c.fmt_mcap(f13['mcap'])} | {f13['filer']} | "
                f"{f13['date']} | {f13['form']} |"
            )
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Discord embeds
# ---------------------------------------------------------------------------

def _build_discord_embeds(clusters: list[dict], notable: list[dict],
                          filings_13d: list[dict]) -> list[dict]:
    """Build Discord embed objects for webhook posting."""
    embeds = []

    for cl in clusters:
        insider_lines = []
        for ins in cl["insiders"]:
            insider_lines.append(
                f"• {ins['insider']} ({ins['role']}) — "
                f"{ins['shares']:,.0f} shares @ ${ins['price']:.2f}"
            )
        signals = cl.get("signals", [])
        signal_str = ""
        if signals:
            tags = []
            if "dip" in signals:
                tags.append("DIP BUY")
            if "rip" in signals:
                tags.append("RIP BUY")
            signal_str = " [" + " + ".join(tags) + "]"

        fields = [
            {"name": "Ticker", "value": cl["ticker"], "inline": True},
            {"name": "Market Cap", "value": c.fmt_mcap(cl["mcap"]), "inline": True},
            {"name": "Window", "value": cl["date_range"], "inline": True},
            {"name": "Insiders", "value": str(cl["num_insiders"]), "inline": True},
        ]
        z = cl.get("zscore")
        r = cl.get("return_30d")
        if z is not None:
            fields.append({
                "name": "30d Move",
                "value": f"{_return_str(r)} ({_zscore_str(z)})",
                "inline": True,
            })

        embeds.append({
            "title": (f"\U0001f7e2 Insider Cluster Buy — "
                      f"{cl['ticker']} ({cl['company']}){signal_str}"),
            "url": f"https://finance.yahoo.com/quote/{cl['ticker']}",
            "color": 0x2ecc71,
            "description": "\n".join(insider_lines),
            "fields": fields,
        })

    # Notable singles — only post the most extreme (top 10)
    for n in notable[:10]:
        signal = n.get("signal", "")
        if signal == "dip":
            emoji = "\U0001f4c9"  # 📉
            color = 0x3498db      # blue
            label = "Dip Buy"
        else:
            emoji = "\U0001f4c8"  # 📈
            color = 0xe74c3c      # red
            label = "Rip Buy"

        embeds.append({
            "title": (f"{emoji} {label} — "
                      f"{n['ticker']} ({n['company']})"),
            "url": f"https://finance.yahoo.com/quote/{n['ticker']}",
            "color": color,
            "description": (f"• {n['insider']} ({n['role']}) — "
                            f"{n['shares']:,.0f} shares @ ${n['price']:.2f}"),
            "fields": [
                {"name": "30d Move", "value": _return_str(n.get("return_30d")),
                 "inline": True},
                {"name": "Z-Score", "value": _zscore_str(n.get("zscore")),
                 "inline": True},
                {"name": "Market Cap", "value": c.fmt_mcap(n.get("mcap")),
                 "inline": True},
            ],
        })

    for f13 in filings_13d:
        embeds.append({
            "title": (f"\U0001f3db\ufe0f Activist 13D — "
                      f"{f13['ticker']} ({f13['company']})"),
            "url": f"https://finance.yahoo.com/quote/{f13['ticker']}",
            "color": 0xe67e22,
            "fields": [
                {"name": "Filer", "value": f13["filer"], "inline": True},
                {"name": "Market Cap", "value": c.fmt_mcap(f13["mcap"]),
                 "inline": True},
                {"name": "Date", "value": f13["date"], "inline": True},
            ],
        })

    return embeds


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Scan Form 4 cluster buys, rip/dip buys, and 13D filings."
    )
    p.add_argument(
        "--date", required=True,
        help='Filing date to scan (YYYY-MM-DD, "today", or "yesterday").',
    )
    p.add_argument(
        "--lookback", type=int, default=5,
        help="Days to look back for cluster detection (default: 5).",
    )
    p.add_argument(
        "--zscore", type=float, default=1.5,
        help="Z-score threshold for rip/dip tagging (default: 1.5).",
    )
    p.add_argument(
        "--webhook",
        help="Discord webhook URL (optional; if omitted, no Discord post).",
    )
    c.add_identity_arg(p)
    c.add_cache_arg(p)
    args = p.parse_args()

    c.resolve_identity(args.identity)
    cache = c.cache_root(args.cache_dir)

    end_date = c.parse_date(args.date)
    dates = _trading_dates(end_date, args.lookback)
    c.log(f"Scanning {len(dates)} trading days: {dates[0]} to {dates[-1]}")

    mcap_data = c.load_mcap_cache(cache)

    try:
        purchases = scan_form4s(dates, cache, mcap_data)
        filings_13d = scan_13d(dates, cache, mcap_data)

        # Tag rip/dip on all purchases
        if purchases:
            tag_rip_dip(purchases, zscore_threshold=args.zscore)

        # Detect clusters
        clusters = detect_clusters(purchases)
        cluster_tickers = set(cl["ticker"] for cl in clusters)

        # Collect notable singles (rip/dip that aren't in a cluster)
        notable = collect_notable_singles(purchases, cluster_tickers)
    finally:
        c.save_mcap_cache(cache, mcap_data)

    total_rip = sum(1 for t in purchases.values() for b in t
                    if b.get("signal") == "rip")
    total_dip = sum(1 for t in purchases.values() for b in t
                    if b.get("signal") == "dip")
    c.log(f"Found {len(clusters)} cluster buys, "
          f"{total_rip} rip buys, {total_dip} dip buys, "
          f"{len(filings_13d)} 13D filings")

    md = _build_markdown(purchases, clusters, notable, filings_13d, dates,
                          mcap_data)
    slug = end_date
    c.write_output(cache, "insiders", slug, md)
    print(md)

    if args.webhook:
        embeds = _build_discord_embeds(clusters, notable, filings_13d)
        if embeds:
            c.log(f"Posting {len(embeds)} embeds to Discord...")
            _post_discord(args.webhook, embeds)
            c.log("Discord post complete.")
        else:
            c.log("No embeds to post to Discord.")


if __name__ == "__main__":
    main()
