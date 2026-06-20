r"""Discover companies presenting at investor conferences via 8-K filings.

Two-stage pipeline:
  Stage 1 — EFTS server-side pre-filter (cheap, no downloads):
    Run targeted full-text queries against EDGAR's search index, optionally
    filtered by item number. Merge results and deduplicate by accession number.

  Stage 2 — Client-side text classification (download & parse):
    For each candidate, download the actual filing HTML and apply:
      2a. Exclusion check  — reject if every occurrence of the signal word
                             is inside a known false-positive phrase.
      2b. Attendance check — accept only if an attendance verb pattern matches.
    Some query types (investor day, capital markets day) skip Stage 2 entirely
    because the signal is reliable enough from EFTS + item filter alone, and
    the keyword often lives in the exhibit rather than the HTML body.

Usage:
    python scripts/scan_conferences.py --start 2026-06-16 --end 2026-06-20

    # override classifier params at runtime (useful for testing)
    python scripts/scan_conferences.py --start 2026-06-16 --end 2026-06-20 \\
        --params '{"exclusions": ["conference call", "conference call and webcast"]}'
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c

# ---------------------------------------------------------------------------
# Default classifier parameters
# All three lists are tunable — start minimal, add one element at a time.
# ---------------------------------------------------------------------------
DEFAULT_PARAMS: dict = {
    # Stage 1: EFTS full-text queries.
    # Key   = quoted string exactly as passed to edgar.search_filings(query=...)
    # Value = item filter string (or None for no filter)
    "queries": {
        "conference": None,  # backbone — ~226/week, needs Stage 2
        '"fireside chat"': None,  # ~8/week, near-zero noise
        "symposium": None,  # ~4/week, clean
        '"forum"': "7.01",  # ~408/week with 7.01; Stage 2 clears boilerplate
        '"investor day"': "8.01",  # ~2/week, own-hosted events; skip Stage 2
        '"capital markets day"': None,  # <1/week, European names; skip Stage 2
    },
    # Queries where keyword is often in exhibit only or signal is reliable
    # enough from EFTS+item filter — skip Stage 2 text classification.
    "no_text_check_queries": ['"investor day"', '"capital markets day"'],
    # Stage 2a: reject if EVERY occurrence of the signal word sits inside one
    # of these phrases (case-insensitive substring match in a ±60-char window).
    "exclusions": [
        "conference call",
        "conference call and webcast",
        "exclusive forum",
        "forum selection",
        "alternative forum",
    ],
    # Stage 2b: accept if at least one of these patterns matches (re.IGNORECASE).
    # Keep minimal — add only when a real filing fails to match.
    "patterns": [
        r"will present",
        r"presenting at",
        r"participate in",
        r"scheduled to present",
        r"speak at",
        r"participation at",
        r"will attend",
        r"will be attending",
    ],
}


# ---------------------------------------------------------------------------
# Stage 2 helpers
# ---------------------------------------------------------------------------


def _all_occurrences_excluded(text: str, signal_word: str, exclusions: list[str]) -> bool:
    """Return True only if EVERY occurrence of signal_word in text is contained within an exclusion-phrase context (±60 chars).

    Logic: if even one occurrence is NOT in an exclusion context, the filing
    may be genuine — don't reject it.
    """
    positions = [m.start() for m in re.finditer(re.escape(signal_word), text, re.IGNORECASE)]

    if not positions:
        return False  # word not found → can't reject on this basis

    for pos in positions:
        window = text[max(0, pos - 60) : pos + 60 + len(signal_word)].lower()
        if not any(ex.lower() in window for ex in exclusions):
            return False  # found at least one occurrence outside exclusions

    return True  # every occurrence was inside an exclusion phrase


def _has_attendance_verb(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _classify(text: str, query: str, params: dict) -> str:
    """Apply Stage 2 classification.

    Returns one of: "ACCEPT" | "REJECT_EXCLUSION" | "REJECT_NO_PATTERN" | "SKIP_NO_TEXT".
    """
    # Some queries trust EFTS + item filter — skip text check entirely.
    if query in params["no_text_check_queries"]:
        return "ACCEPT"

    # The signal word is the first meaningful word of the query.
    signal_word = query.strip('"').split()[0]

    # If the signal word isn't in the HTML body at all, the match was in an
    # exhibit — we can't classify it, so skip rather than false-accept.
    if not re.search(re.escape(signal_word), text, re.IGNORECASE):
        return "SKIP_NO_TEXT"

    # 2a — exclusion check
    if _all_occurrences_excluded(text, signal_word, params["exclusions"]):
        return "REJECT_EXCLUSION"

    # 2b — attendance verb check
    if _has_attendance_verb(text, params["patterns"]):
        return "ACCEPT"

    return "REJECT_NO_PATTERN"


# ---------------------------------------------------------------------------
# Stage 1: EFTS candidate retrieval
# ---------------------------------------------------------------------------


def _get_candidates(start: str, end: str, params: dict, limit: int = 300) -> dict[str, dict]:
    """Run all EFTS queries, merge results, deduplicate by accession number.

    Returns {accession_number: {"result": EFTSResult, "query": str}}.
    First-match wins on deduplication (queries are ordered by signal quality).
    """
    import edgar

    candidates: dict[str, dict] = {}

    for query, item_filter in params["queries"].items():
        c.log(f"  EFTS: {query!r}" + (f" items={item_filter!r}" if item_filter else "") + " ...")
        try:
            results = edgar.search_filings(
                query=query,
                forms="8-K",
                items=item_filter,
                start_date=start,
                end_date=end,
                limit=limit,
            )
            if results is None:
                continue
            n = 0
            for r in results:
                acc = getattr(r, "accession_number", "") or ""
                if not acc:
                    continue
                if acc not in candidates:
                    candidates[acc] = {"result": r, "query": query}
                    n += 1
            c.log(f"    → {n} new candidates")
        except Exception as exc:
            c.log(f"    ERROR: {exc}")

    return candidates


# ---------------------------------------------------------------------------
# Conference name extractor
# ---------------------------------------------------------------------------


def _extract_conference_name(text: str) -> str | None:
    """Try to pull a conference / event name out of the filing text.

    Returns a clean string or None.
    """
    patterns = [
        r"(?:at|the)\s+([\w\s&\-\']{10,80}?"
        r"(?:Conference|Forum|Symposium|Investor Day|Capital Markets Day|Fireside Chat))",
        r"(?:will present at|presenting at|participate in|speak at)\s+(?:the\s+)?([^.]{10,80})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            name = re.sub(r"[.,;:\s]+$", "", m.group(1)).strip()
            if len(name) >= 10:
                return name[:120]
    return None


# ---------------------------------------------------------------------------
# Main scan function
# ---------------------------------------------------------------------------


def scan_conferences(start: str, end: str, params: dict, mcap_data: dict) -> list[dict]:
    """Run the full two-stage pipeline and return a list of conference dicts."""
    c.log(f"Scanning 8-K filings for conferences: {start} to {end}")

    candidates = _get_candidates(start, end, params)
    c.log(f"  {len(candidates)} unique candidates after EFTS + dedup")

    if not candidates:
        return []

    conferences = []
    stats = {
        "checked": 0,
        "no_ticker": 0,
        "out_of_universe": 0,
        "no_text": 0,
        "rejected": 0,
        "accepted": 0,
    }

    for acc, cand in candidates.items():
        r = cand["result"]
        query = cand["query"]
        stats["checked"] += 1

        # ── resolve ticker ──────────────────────────────────────────────────
        company_raw = str(getattr(r, "company", "Unknown"))
        str(getattr(r, "cik", "")).lstrip("0")
        filed = str(getattr(r, "filed", ""))

        # Ticker is in the EFTS company string: "NAME  (TICK)  (CIK ...)"
        m = re.search(r"\(([A-Z]{1,5})\)", company_raw)
        if not m:
            stats["no_ticker"] += 1
            continue
        ticker = m.group(1)

        # ── universe filter (market cap $50M-$10B) ──────────────────────────
        mcap = c.get_market_cap(ticker, mcap_data)
        if not c.in_universe(mcap):
            stats["out_of_universe"] += 1
            continue

        # ── fetch filing text ───────────────────────────────────────────────
        filing_text = ""
        try:
            filing_text = r.get_filing().text()
        except Exception as exc:
            c.log(f"  WARN: could not fetch text for {acc}: {exc}")

        if not filing_text:
            stats["no_text"] += 1
            continue

        # ── Stage 2 classification ──────────────────────────────────────────
        verdict = _classify(filing_text, query, params)

        if verdict != "ACCEPT":
            stats["rejected"] += 1
            continue

        stats["accepted"] += 1

        # ── enrich with yfinance ────────────────────────────────────────────
        try:
            import yfinance as yf

            info = yf.Ticker(ticker).info or {}
        except Exception:
            info = {}

        conferences.append(
            {
                "ticker": ticker,
                "company": info.get("shortName") or info.get("longName") or company_raw,
                "sector": info.get("sector", "n/a"),
                "mcap": mcap,
                "price": info.get("currentPrice"),
                "filed": filed,
                "conference": _extract_conference_name(filing_text) or "(see filing)",
                "query": query,  # which EFTS query surfaced this
            }
        )

    c.log(f"  Done — {stats}")
    return conferences


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _render_markdown(start: str, end: str, conferences: list[dict]) -> str:
    lines = [
        f"# Conference Discovery: {start} to {end}\n",
        f"Found **{len(conferences)}** companies in the {c.universe_label()} universe.\n",
    ]

    if not conferences:
        lines.append("No conference announcements found.\n")
        return "\n".join(lines)

    lines += [
        "| # | Ticker | Company | Sector | Mkt Cap | Price | Filed | Conference |",
        "|---|--------|---------|--------|---------|-------|-------|------------|",
    ]
    for i, conf in enumerate(conferences, 1):
        price_s = f"${conf['price']:.2f}" if conf.get("price") else "n/a"
        lines.append(
            f"| {i} | {conf['ticker']} | {conf['company']} | {conf['sector']} | "
            f"{c.fmt_mcap(conf['mcap'])} | {price_s} | {conf['filed']} | "
            f"{conf['conference']} |"
        )

    lines.append(
        "\n_Sourced from 8-K filings via EFTS full-text search + "
        "two-stage client-side classifier._\n"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the CLI to discover companies presenting at investor conferences."""
    p = argparse.ArgumentParser(
        description="Conference discovery via 8-K filings (two-stage EFTS classifier)."
    )
    p.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    p.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    p.add_argument(
        "--params",
        help="JSON string to override/extend DEFAULT_PARAMS keys. "
        'Example: \'{"exclusions": ["conference call"]}\'',
    )
    c.add_identity_arg(p)
    c.add_cache_arg(p)
    args = p.parse_args()

    c.resolve_identity(args.identity)

    # edgartools needs system certs on corporate networks
    try:
        from edgar import configure_http

        configure_http(use_system_certs=True)
    except Exception:
        pass

    params = {
        k: (v.copy() if isinstance(v, (dict, list)) else v) for k, v in DEFAULT_PARAMS.items()
    }
    if args.params:
        try:
            overrides = json.loads(args.params)
            params.update(overrides)
        except json.JSONDecodeError as exc:
            c.log(f"ERROR: invalid --params JSON: {exc}")
            sys.exit(1)

    cache = c.cache_root(args.cache_dir)
    mcap_data = c.load_mcap_cache(cache)

    try:
        conferences = scan_conferences(args.start, args.end, params, mcap_data)
    finally:
        c.save_mcap_cache(cache, mcap_data)

    md = _render_markdown(args.start, args.end, conferences)
    slug = f"{args.start}_to_{args.end}"
    c.write_output(cache, "conferences", slug, md)


if __name__ == "__main__":
    main()
