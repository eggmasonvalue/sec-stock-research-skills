"""Minimal shared runtime setup for market-scout scripts."""

import sys

# yfinance/pandas can emit non-ASCII text (e.g. company names like "Société");
# force UTF-8 so a Windows cp1252 console doesn't raise UnicodeEncodeError.
if sys.platform.startswith("win"):
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def log(msg: str) -> None:
    """Progress/diagnostics -> stderr (keeps stdout clean for the result)."""
    print(msg, file=sys.stderr, flush=True)
