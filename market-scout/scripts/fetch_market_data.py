"""Fetch market data via yfinance: price snapshot, trailing returns, peers.

The core tool of the market-scout skill (Yahoo Finance). Output is a compact
Markdown summary printed to stdout — market data is small and time-sensitive, so
it is never cached to disk. Two modes compose: a per-name snapshot, and (with
``--industry`` / ``--peers``) a sector view useful as a discovery top-of-funnel.
Run ``--help`` for all flags.
"""

import argparse
import sys

import _common as c

_RETURN_WINDOWS = [("1M", 30), ("3M", 91), ("6M", 182), ("1Y", 365), ("3Y", 1095), ("5Y", 1825)]


def _num(v, money=False, pct=False):
    if v is None:
        return "n/a"
    try:
        if pct:
            return f"{v:+.1f}%"
        if money:
            return f"{v:,.0f}"
        return f"{v:,.2f}"
    except Exception:
        return str(v)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ticker", required=True, help="Stock ticker (Yahoo symbol).")
    p.add_argument("--period", default="5y", help="History window for returns (default: 5y).")
    p.add_argument("--industry", action="store_true", help="Also print the industry overview.")
    p.add_argument("--peers", action="store_true", help="Also list industry peers by weight.")
    args = p.parse_args()

    try:
        import pandas as pd
        import yfinance as yf
    except Exception as exc:
        c.log(f"ERROR: yfinance/pandas not installed: {exc}")
        sys.exit(1)

    ticker = yf.Ticker(args.ticker)
    try:
        info = ticker.info or {}
    except Exception as exc:
        c.log(f"WARNING: could not fetch .info: {exc}")
        info = {}

    print(f"# Market data: {args.ticker.upper()}\n")
    print("## Snapshot")
    print(f"- Price: {_num(info.get('currentPrice'))}")
    print(f"- Market cap: {_num(info.get('marketCap'), money=True)}")
    print(f"- Shares outstanding: {_num(info.get('sharesOutstanding'), money=True)}")
    print(
        f"- 52-week high / low: {_num(info.get('fiftyTwoWeekHigh'))} / "
        f"{_num(info.get('fiftyTwoWeekLow'))}"
    )
    if info.get("sector") or info.get("industry"):
        print(
            f"- Sector / industry: {info.get('sector') or 'n/a'} / {info.get('industry') or 'n/a'}"
        )

    try:
        close = ticker.history(period=args.period)["Close"].dropna()
        if len(close) > 1:
            last, last_date = close.iloc[-1], close.index[-1]
            print("\n## Trailing returns")
            for label, days in _RETURN_WINDOWS:
                prior = close[close.index <= last_date - pd.Timedelta(days=days)]
                if len(prior):
                    print(f"- {label}: {_num((last / prior.iloc[-1] - 1) * 100, pct=True)}")
    except Exception as exc:
        c.log(f"WARNING: returns unavailable: {exc}")

    if args.industry or args.peers:
        industry_key = info.get("industryKey")
        if not industry_key:
            c.log("WARNING: no industryKey in .info; cannot fetch industry/peers.")
        else:
            try:
                industry = yf.Industry(industry_key)
                if args.industry:
                    overview = industry.overview or {}
                    print(f"\n## Industry: {getattr(industry, 'name', industry_key)}")
                    if overview.get("market_cap"):
                        print(f"- Total market cap: {_num(overview['market_cap'], money=True)}")
                    if overview.get("companies_count"):
                        print(f"- Companies: {overview['companies_count']}")
                    if overview.get("description"):
                        print(f"- {overview['description']}")
                if args.peers:
                    top = industry.top_companies
                    if top is not None and len(top):
                        print("\n## Top peers by market weight")
                        head = top.head(15)
                        try:
                            print(head.to_markdown())
                        except Exception:
                            print(head.to_string())
            except Exception as exc:
                c.log(f"WARNING: industry/peers unavailable: {exc}")


if __name__ == "__main__":
    main()
