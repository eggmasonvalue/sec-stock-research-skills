"""Shared bootstrap for signal-sweep scripts.

Follows the same conventions as sec-edgar-skill and market-scout:
  * UTF-8 stdout/stderr on Windows
  * truststore injection for corporate proxy SSL
  * log() -> stderr, emit() -> stdout
  * SEC identity resolution
  * Market-cap cache (yfinance lookups are expensive at scale)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# --- Runtime setup (runs once, on import) ---------------------------------
if sys.platform.startswith("win"):
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass


def log(msg: str) -> None:
    """Human-readable progress -> stderr (keeps stdout clean for results)."""
    print(msg, file=sys.stderr, flush=True)


def emit(path: "str | os.PathLike") -> None:
    """Machine-readable result -> stdout: one absolute path per line."""
    print(str(Path(path).resolve()))


# --- SEC identity ---------------------------------------------------------
def resolve_identity(cli_value: "str | None" = None) -> str:
    """Return the SEC identity or exit(2) with an actionable message."""
    identity = cli_value or os.environ.get("EDGAR_IDENTITY")
    if not identity or "@" not in identity:
        log(
            "ERROR: a SEC identity is required (SEC fair-access policy). Set it:\n"
            '  PowerShell:  $env:EDGAR_IDENTITY = "Jane Analyst jane@example.com"\n'
            '  Bash:        export EDGAR_IDENTITY="Jane Analyst jane@example.com"\n'
            'or pass --identity "Name email@example.com".'
        )
        sys.exit(2)
    from edgar import set_identity
    set_identity(identity)
    return identity


def add_identity_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--identity",
        help='SEC User-Agent "Name email@example.com" (else uses $EDGAR_IDENTITY).',
    )


# --- Output cache ---------------------------------------------------------
def cache_root(cli_value: "str | None" = None) -> Path:
    """Resolve cache root: --cache-dir > $SIGNAL_SWEEP_CACHE > ./signal-sweep-cache."""
    root = cli_value or os.environ.get("SIGNAL_SWEEP_CACHE") or "signal-sweep-cache"
    return Path(root).resolve()


def add_cache_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cache-dir",
        help="Cache root (default: $SIGNAL_SWEEP_CACHE or ./signal-sweep-cache).",
    )


def write_output(cache: Path, capability: str, slug: str, content: str) -> Path:
    """Write Markdown output to cache and emit the path.

    File layout: signal-sweep-cache/{capability}/{slug}.md
    """
    out_dir = cache / capability
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.md"
    out_path.write_text(content, encoding="utf-8")
    emit(out_path)
    return out_path


# --- Market-cap cache (disk-backed, 24h TTL) ------------------------------
_MCAP_CACHE_FILE = "mcap_cache.json"
_MCAP_TTL_HOURS = 24


def _mcap_cache_path(cache: Path) -> Path:
    return cache / _MCAP_CACHE_FILE


def load_mcap_cache(cache: Path) -> dict:
    """Load {ticker: {"mcap": int, "sector": str, "ts": float}} from disk."""
    p = _mcap_cache_path(cache)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_mcap_cache(cache: Path, data: dict) -> None:
    p = _mcap_cache_path(cache)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data), encoding="utf-8")


def get_market_cap(ticker: str, mcap_data: dict, *, force: bool = False) -> int | None:
    """Look up market cap via yfinance, using disk cache with TTL.

    Returns market cap in dollars, or None if lookup fails.
    Also caches sector for downstream summary use.
    """
    import yfinance as yf

    now = time.time()
    cutoff = now - _MCAP_TTL_HOURS * 3600

    if not force and ticker in mcap_data:
        entry = mcap_data[ticker]
        if entry.get("ts", 0) > cutoff:
            return entry.get("mcap")

    try:
        info = yf.Ticker(ticker).info or {}
        mcap = info.get("marketCap")
        if mcap is not None:
            mcap_data[ticker] = {
                "mcap": int(mcap),
                "sector": info.get("sector", ""),
                "shares_out": info.get("sharesOutstanding"),
                "ts": now,
            }
        return mcap
    except Exception:
        return None


def get_cached_sector(ticker: str, mcap_data: dict) -> str:
    """Return the cached sector for a ticker, or 'Unknown'."""
    entry = mcap_data.get(ticker, {})
    return entry.get("sector", "") or "Unknown"


def get_cached_shares_out(ticker: str, mcap_data: dict) -> int | None:
    """Return the cached shares outstanding for a ticker, or None."""
    entry = mcap_data.get(ticker, {})
    return entry.get("shares_out")


def in_universe(mcap: int | None, floor: int = 50_000_000, ceiling: int = 10_000_000_000) -> bool:
    """Check whether a market cap falls within the scan universe."""
    if mcap is None:
        return False
    return floor <= mcap <= ceiling


def fmt_mcap(mcap: int | None) -> str:
    """Format market cap for display: $1.2B, $890M, etc."""
    if mcap is None:
        return "n/a"
    if mcap >= 1_000_000_000:
        return f"${mcap / 1_000_000_000:.1f}B"
    if mcap >= 1_000_000:
        return f"${mcap / 1_000_000:.0f}M"
    return f"${mcap:,.0f}"


def parse_date(s: str) -> str:
    """Parse 'YYYY-MM-DD', 'today', or 'yesterday' into YYYY-MM-DD string."""
    if s.lower() == "today":
        return datetime.now().strftime("%Y-%m-%d")
    if s.lower() == "yesterday":
        d = datetime.now() - timedelta(days=1)
        return d.strftime("%Y-%m-%d")
    # Validate format
    datetime.strptime(s, "%Y-%m-%d")
    return s
