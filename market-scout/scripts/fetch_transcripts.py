"""Fetch earnings call transcripts from Yahoo Finance for a given ticker.

Uses ``agent-browser`` (a browser automation CLI) to scrape the
public Yahoo Finance earnings-call pages (powered by Quartr). Yahoo Finance
requires JavaScript rendering and blocks plain HTTP clients, so a real browser
is the only reliable approach.

Two modes:

  --list    Print the available transcripts (title + URL) without downloading.
  (default) Download all (or a filtered subset) and write to the cache.

Filtering: ``--latest N`` grabs only the N most recent calls; ``--quarter``
and ``--year`` narrow to a specific period (e.g. ``--year 2025 --quarter Q3``).

Output is one ``.md`` file per transcript, structured for LLM consumption:
  - Front-matter metadata (ticker, quarter, date, source URL)
  - AI-generated summary (when Yahoo provides one)
  - Full transcript with Markdown headings per speaker turn, making it
    greppable and easy to jump to a specific speaker or Q&A section.

Files are written to ``<cache>/<TICKER>/transcripts/`` and absolute paths are
printed to stdout (one per line). Progress goes to stderr.

Prerequisite: ``agent-browser`` must be installed and on PATH.
Run ``--help`` for the full flag reference.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import _common as c

_BASE = "https://finance.yahoo.com"
_DELAY = 2.0  # polite delay between page fetches (seconds)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _cache_root(cli_value: str | None = None) -> Path:
    root = cli_value or os.environ.get("TRANSCRIPT_CACHE_DIR") or "transcript-cache"
    return Path(root).resolve()


def _safe(part: str) -> str:
    return re.sub(r"[^\w\-.]", "-", str(part)).strip("-") or "x"


def _transcript_dir(root: Path, ticker: str) -> Path:
    d = root / ticker.upper() / "transcripts"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# agent-browser helpers
# ---------------------------------------------------------------------------


def _find_agent_browser() -> str:
    import shutil

    for name in ["agent-browser", "agent-browser.cmd"]:
        found = shutil.which(name)
        if found:
            return found
    return "agent-browser"


def _run_agent_browser(args: list[str], timeout: int = 45) -> str:
    """Run an agent-browser command and return stdout."""
    exe = _find_agent_browser()
    try:
        result = subprocess.run(
            [exe, *args],
            capture_output=True,
            text=True,
            timeout=timeout + 15,
            shell=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if stderr:
                c.log(f"  agent-browser stderr: {stderr[:300]}")
            return ""
        return result.stdout.strip()
    except FileNotFoundError:
        c.log(
            "ERROR: agent-browser is not installed or not on PATH.\n"
            "Install it:  npm install -g agent-browser && agent-browser install"
        )
        sys.exit(2)
    except subprocess.TimeoutExpired:
        c.log("WARNING: agent-browser command timed out.")
        return ""


def _open_url(url: str, timeout: int = 45) -> bool:
    return bool(_run_agent_browser(["open", url], timeout=timeout))


def _run_browser_script(script: str, timeout: int = 45) -> str:
    """Run page-context JS via `agent-browser eval`, return stdout."""
    b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
    out = _run_agent_browser(["eval", "-b", b64], timeout=timeout)
    if out.startswith('"') and out.endswith('"'):
        try:
            unwrapped = json.loads(out)
            if isinstance(unwrapped, str):
                return unwrapped
        except Exception:
            pass
    return out


# ---------------------------------------------------------------------------
# Step 1: List available transcripts
# ---------------------------------------------------------------------------


def _fetch_listing(ticker: str) -> list[dict]:
    """Fetch the list of available transcripts for a ticker."""
    url = f"{_BASE}/quote/{ticker}/earnings-calls/"
    if not _open_url(url, timeout=45):
        return []
    time.sleep(3)
    script = 'JSON.stringify(Array.from(document.querySelectorAll(\'a[href*="earnings_call"]\')).map(a=>({url:a.getAttribute("href"),title:(a.textContent||"").trim()||a.getAttribute("aria-label")||a.getAttribute("href")})).filter(x=>x.url).filter((x,i,arr)=>arr.findIndex(y=>y.url===x.url)===i))'
    raw = _run_browser_script(script)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        c.log("WARNING: could not parse listing response.")
        return []


# ---------------------------------------------------------------------------
# Step 2: Fetch a single transcript
# ---------------------------------------------------------------------------


def _fetch_transcript(url: str) -> dict | None:
    """Fetch and parse a single transcript page."""
    full_url = f"{_BASE}{url}" if url.startswith("/") else url
    if not _open_url(full_url, timeout=50):
        return None
    time.sleep(4)
    script = r"""
JSON.stringify((() => {
  const main = document.querySelector("main");
  if (!main) return { error: "no main element" };
  const h1 = main.querySelector("h1");
  const title = h1 ? h1.textContent.trim() : "";
  const dateMatch = document.body.textContent.match(
    /[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4},?\s+\d{1,2}:\d{2}\s+[AP]M\s+\w+/
  );
  const date = dateMatch ? dateMatch[0] : "";
  const summaryP = document.querySelector(".summary p");
  const summary = summaryP ? summaryP.textContent.trim() : "";
  const items = document.querySelectorAll(".items > .item");
  const blocks = [];
  for (const item of items) {
    const speakerSpan = item.querySelector(".speakerInfo > span");
    const speakerDesc = item.querySelector(".speakerDesc");
    const headline = item.querySelector(".headline");
    const timestampP = headline ? headline.querySelector("p") : null;
    const contentP = item.querySelector(":scope > p");
    const speaker = speakerSpan ? speakerSpan.textContent.trim() : "Unknown";
    const role = speakerDesc ? speakerDesc.textContent.trim() : "";
    const timestamp = timestampP ? timestampP.textContent.trim() : "";
    const text = contentP ? contentP.textContent.trim() : "";
    if (text) {
      blocks.push({ speaker, role, timestamp, text });
    }
  }
  return { title, date, summary, blocks };
})())
"""
    raw = _run_browser_script(script, timeout=50)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if data.get("error"):
            c.log(f"    WARNING: {data['error']}")
            return None
        return data
    except json.JSONDecodeError:
        c.log("WARNING: could not parse transcript response.")
        return None


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _render_markdown(ticker: str, url: str, data: dict) -> str:
    """Render a parsed transcript as LLM-friendly Markdown."""
    lines = []
    lines.append(f"# {data['title']}")
    lines.append("")
    lines.append(f"- **Ticker:** {ticker.upper()}")
    if data.get("date"):
        lines.append(f"- **Date:** {data['date']}")
    full_url = f"{_BASE}{url}" if url.startswith("/") else url
    lines.append(f"- **Source:** {full_url}")
    lines.append("")

    if data.get("summary"):
        lines.append("## Summary")
        lines.append("")
        lines.append(data["summary"])
        lines.append("")

    # Detect Q&A boundary: first Operator turn after prepared remarks that
    # mentions "question" (the standard transition phrase).
    qa_index = None
    found_non_operator = False
    for i, block in enumerate(data.get("blocks", [])):
        if block["speaker"] != "Operator":
            found_non_operator = True
        elif found_non_operator and "question" in block["text"].lower():
            qa_index = i
            break

    lines.append("## Prepared Remarks")
    lines.append("")

    prev_speaker = None
    for i, block in enumerate(data.get("blocks", [])):
        if qa_index is not None and i == qa_index:
            lines.append("")
            lines.append("## Q&A")
            lines.append("")

        speaker_label = block["speaker"]
        if block.get("role"):
            speaker_label += f" — {block['role']}"

        if block["speaker"] != prev_speaker:
            lines.append(f"### {speaker_label}")
            lines.append("")
            prev_speaker = block["speaker"]

        lines.append(block["text"])
        lines.append("")

    return "\n".join(lines)


def _filename_from_title(title: str) -> str:
    """Convert 'CMTL Q3 FY2026 earnings call transcript' -> 'Q3-FY2026.md'."""
    m = re.search(r"(Q\d)\s+(FY\d{4})", title, re.IGNORECASE)
    if m:
        return f"{m.group(1).upper()}-{m.group(2).upper()}.md"
    return _safe(title[:60]) + ".md"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    p = argparse.ArgumentParser(description="Fetch earnings call transcripts from Yahoo Finance.")
    p.add_argument("--ticker", required=True, help="Stock ticker (Yahoo symbol).")
    p.add_argument(
        "--list", action="store_true", help="List available transcripts without downloading."
    )
    p.add_argument(
        "--latest", type=int, default=0, help="Download only the N most recent transcripts."
    )
    p.add_argument(
        "--quarter", type=str, default=None, help="Filter to a specific quarter (e.g. Q3)."
    )
    p.add_argument(
        "--year", type=int, default=None, help="Filter to a specific fiscal year (e.g. 2025)."
    )
    p.add_argument(
        "--cache-dir",
        default=None,
        help="Cache root (default: $TRANSCRIPT_CACHE_DIR or ./transcript-cache).",
    )
    args = p.parse_args()

    ticker = args.ticker.upper()

    # Step 1: Fetch listing
    c.log(f"Fetching transcript listing for {ticker}...")
    transcripts = _fetch_listing(ticker)
    if not transcripts:
        c.log(f"No earnings call transcripts found for {ticker}.")
        sys.exit(0)

    c.log(f"Found {len(transcripts)} transcript(s) for {ticker}.")

    # Apply filters
    if args.quarter:
        q = args.quarter.upper()
        transcripts = [t for t in transcripts if q in t["title"].upper()]
    if args.year:
        y = str(args.year)
        transcripts = [t for t in transcripts if y in t["title"]]
    if args.latest and args.latest > 0:
        transcripts = transcripts[: args.latest]

    if args.list:
        print(f"# Earnings call transcripts for {ticker}\n")
        for i, t in enumerate(transcripts, 1):
            full_url = f"{_BASE}{t['url']}" if t["url"].startswith("/") else t["url"]
            print(f"{i}. [{t['title']}]({full_url})")
        sys.exit(0)

    if not transcripts:
        c.log("No transcripts match the filter criteria.")
        sys.exit(0)

    # Step 2: Download each transcript
    root = _cache_root(args.cache_dir)
    out_dir = _transcript_dir(root, ticker)
    c.log(f"Saving to: {out_dir}")

    for i, t in enumerate(transcripts):
        fname = _filename_from_title(t["title"])
        out_path = out_dir / fname

        if out_path.exists():
            c.log(f"  [{i + 1}/{len(transcripts)}] Already cached: {fname}")
            print(str(out_path.resolve()))
            continue

        c.log(f"  [{i + 1}/{len(transcripts)}] Downloading: {t['title']}")
        data = _fetch_transcript(t["url"])
        if not data or not data.get("blocks"):
            c.log("    WARNING: no transcript content found, skipping.")
            continue

        md = _render_markdown(ticker, t["url"], data)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(md, encoding="utf-8")
        block_count = len(data.get("blocks", []))
        c.log(f"    Saved: {fname} ({block_count} speaker turns)")
        print(str(out_path.resolve()))

        if i < len(transcripts) - 1:
            time.sleep(_DELAY)

    c.log("Done.")


if __name__ == "__main__":
    main()
