"""Shared bootstrap and conventions for the sec-edgar-skill scripts.

Importing this module gives every script identical, correct runtime setup with
zero duplication:
  * UTF-8 stdout/stderr on Windows (edgartools' rich reprs contain emoji that
    raise UnicodeEncodeError on cp1252 consoles),
  * truststore injected into SSL when available (so HTTPS works behind an
    inspecting corporate proxy instead of raising CERTIFICATE_VERIFY_FAILED).

It also centralises the two contracts that must stay identical across every
script: the SEC identity requirement, and the on-disk cache layout. Keeping
them here is why a filing cached by one script is found by the others.

Output convention: human-readable progress goes to stderr via ``log``; the
machine-readable result (always an absolute path) goes to stdout via ``emit``,
so a calling agent can capture the path without parsing log noise.
"""

from __future__ import annotations

import argparse
import os
import sys
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


def emit(path: str | os.PathLike) -> None:
    """Machine-readable result -> stdout: one absolute path per line."""
    print(str(Path(path).resolve()))


# --- SEC identity: a mechanical requirement, never a silent default -------
def resolve_identity(cli_value: str | None = None) -> str:
    """Return the SEC identity or exit(2) with an actionable message.

    The SEC fair-access policy requires a real ``Name email`` User-Agent;
    requests without one are blocked with HTTP 403. We deliberately do NOT
    fall back to a fake default, because sending bogus contact information
    abuses the policy and risks the host IP being rate-limited or blocked.
    """
    identity = cli_value or os.environ.get("EDGAR_IDENTITY")
    if not identity or "@" not in identity:
        log(
            "ERROR: a SEC identity is required (SEC fair-access policy; missing "
            "it returns HTTP 403). Set it once:\n"
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


# --- Cache contract -------------------------------------------------------
def cache_root(cli_value: str | None = None) -> Path:
    """Resolve the cache root: --cache-dir > $SEC_CACHE_DIR > ./sec-cache.

    Default is workspace-relative and *visible* on purpose:
      * inside the working directory, so the agent's native grep/ripgrep finds
        cached files with no absolute-path gymnastics;
      * persistent across runs, unlike an OS temp dir (which gets purged, which
        would defeat the whole point of caching and re-hit the SEC needlessly);
      * not dot-prefixed, because ripgrep skips dotdirs by default.
    Set $SEC_CACHE_DIR to redirect to an OS cache dir if you want no footprint.
    """
    root = cli_value or os.environ.get("SEC_CACHE_DIR") or "sec-cache"
    return Path(root).resolve()


def add_cache_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cache-dir",
        help="Cache root (default: $SEC_CACHE_DIR or ./sec-cache).",
    )


def safe_component(part: object) -> str:
    """Make a single path component filesystem-safe (e.g. 10-K/A -> 10-K-A)."""
    cleaned = "".join(ch if (ch.isalnum() or ch in "-._") else "-" for ch in str(part))
    return cleaned.strip("-") or "x"


def filing_stem(filing) -> str:
    """Deterministic, collision-free stem: ``FORM_FILINGDATE_ACCESSION``.

    Accession numbers are globally unique and verifiable against SEC, so this
    lets a caller answer "is this already cached?" by globbing the company
    directory instead of re-downloading, and avoids the stale ``latest_*.md``
    anti-pattern (a "latest" name silently goes out of date next quarter).
    """
    parts = [
        safe_component(getattr(filing, "form", "filing")),
        safe_component(getattr(filing, "filing_date", "")),
        safe_component(
            getattr(filing, "accession_no", None) or getattr(filing, "accession_number", "")
        ),
    ]
    return "_".join(p for p in parts if p and p != "x")


def company_dir(root: Path, company, ticker_hint: str | None = None) -> Path:
    """Return (and create) ``<root>/<TICKER>/``; falls back to CIK if unknown."""
    label = ticker_hint
    if not label:
        try:
            tickers = getattr(company, "tickers", None)
            if tickers:
                label = next(iter(tickers))
        except Exception:
            label = None
    if not label:
        label = str(getattr(company, "cik", "unknown"))
    directory = root / safe_component(label).upper()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def resolve_company(ticker_or_cik: str):
    """Look up a Company, exiting(1) with a clean message if it can't resolve."""
    from edgar import Company

    try:
        return Company(ticker_or_cik)
    except Exception as exc:  # surface one clean line to the calling agent
        log(f"ERROR: could not resolve company '{ticker_or_cik}': {exc}")
        sys.exit(1)


def write_text(path: str | os.PathLike, content: str) -> Path:
    """Write UTF-8 text, creating parent directories as needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p
