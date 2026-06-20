"""Print every Markdown heading with its line number — a table of contents.

Use this on a large cached filing to get a structural map (heading -> line),
then target your reads on the exact lines you need instead of scanning pages.
Output is ``<line>:<heading>`` per match.

This keys on Markdown ``#`` headers, so it maps periodic/current reports
(10-K, 10-Q, 20-F, 8-K) well. Heavily tabular free-form filings (e.g. DEF 14A
proxies) convert with few ``#`` headers — for those, read the table of contents
in the filing's opening lines and grep instead.
"""

import argparse
import sys
from pathlib import Path

import _common as c  # noqa: F401  (import sets UTF-8 stdout on Windows)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--file", required=True, help="Path to a cached .md filing.")
    args = p.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with path.open("r", encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if line.startswith("#"):
                print(f"{n}:{line.strip()}")


if __name__ == "__main__":
    main()
