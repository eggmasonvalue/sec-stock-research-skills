"""Diagnose the skill's environment: Python, dependencies, identity, cache dir.

Run this first if anything misbehaves. Add ``--live`` to also make one real SEC
request and confirm end-to-end connectivity (and identity). Exit code is 0 when
everything required is in place, 1 otherwise.
"""

import argparse
import os
import sys

import _common as c

REQUIRED = {
    "edgar": "edgartools (SEC EDGAR client)",
    "pandas": "pandas (dataframes / CSV export)",
}
OPTIONAL = {
    "truststore": "truststore (system-trust TLS — only needed behind a corporate proxy)",
}


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    c.add_identity_arg(p)
    c.add_cache_arg(p)
    p.add_argument(
        "--live", action="store_true", help="Make one live SEC request to verify connectivity."
    )
    args = p.parse_args()

    print("sec-edgar-skill — environment diagnostics")
    print(f"  Python: {sys.version.split()[0]}  ({sys.executable})")

    ok = True
    for mod, desc in REQUIRED.items():
        try:
            m = __import__(mod)
            print(f"  [ok]      {mod} {getattr(m, '__version__', '?')} — {desc}")
        except Exception:
            print(f"  [MISSING] {mod} — {desc}")
            ok = False
    for mod, desc in OPTIONAL.items():
        try:
            m = __import__(mod)
            print(f"  [ok]      {mod} {getattr(m, '__version__', '?')} — {desc}")
        except Exception:
            print(f"  [warn]    {mod} not installed — {desc}")

    identity = args.identity or os.environ.get("EDGAR_IDENTITY")
    if identity and "@" in identity:
        print(f"  [ok]      SEC identity: {identity}")
    else:
        print(
            "  [MISSING] SEC identity — set $EDGAR_IDENTITY or pass --identity "
            "(required for any fetch; missing it returns HTTP 403)."
        )
        ok = False

    print(f"  cache dir: {c.cache_root(args.cache_dir)}")

    if args.live:
        if not ok:
            print("  [skip]    --live skipped: resolve the issues above first.")
        else:
            try:
                c.resolve_identity(args.identity)
                from edgar import Company

                n = len(Company("AAPL").get_filings(form="10-K", year=2023))
                print(f"  [ok]      live SEC request succeeded (AAPL 10-K 2023: {n} filing(s)).")
            except Exception as exc:
                print(f"  [FAIL]    live SEC request failed: {exc}")
                ok = False

    print(f"STATUS: {'OK' if ok else 'ISSUES FOUND'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
