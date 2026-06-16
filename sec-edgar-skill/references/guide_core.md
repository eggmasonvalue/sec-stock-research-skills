# Core — company lookup, filing discovery, and self-help

Start here. This guide covers resolving a company, listing and filtering its filings,
and the two built-in efficiency tools — `.to_context()` previews and the `.docs`
self-help system. `scripts/orient.py` wraps the orientation steps below into one command;
this guide is the mechanics behind it, for when you drive them inline. The other guides
build on these basics.

## Resolve a company

`Company` accepts a ticker, a CIK, or a name:

```python
from edgar import Company
company = Company("AAPL")          # ticker
company = Company("0000320193")    # CIK
company = Company("Apple Inc.")    # name
```

Metadata lives on the object: `company.cik`, `company.name`, `company.sic`, and the
tickers.

> The ticker attribute is `company.tickers` (a list) or `company.get_ticker()` (a
> string). There is no `company.ticker` — accessing it raises `AttributeError`. This
> matters when building a cache path, where you want `company.tickers[0]`.

## List and filter filings

```python
filings = company.get_filings()                              # everything
filings = company.get_filings(form="10-Q", year=2024)        # by form + year
filings = company.get_filings(quarter=4, year=2024)          # by quarter
filings = company.get_filings(date="2023-01-01:2023-12-31")  # by date range
```

Collections support indexing, slicing, and `.latest()`:

```python
latest_10k = company.get_filings(form="10-K").latest()
recent = filings[0:10]
```

## Survey a company's filing mix

`scripts/orient.py` does this for you (with per-form date ranges and the most recent
filings); reach for it first. To do it inline — or to tabulate a custom window — pull the
collection to a DataFrame. This is a neutral mechanic; which forms are relevant to your
question is for you (or the framework driving you) to decide.

```python
df = company.get_filings(date="2024-01-01:2025-12-31").to_pandas()
print(df["form"].value_counts())
```

Survey a multi-year window, not just the latest filing: a company's form set is **not**
fixed over time — it can change as the company's circumstances do (for instance its
domestic-vs-foreign reporting status, a recent listing, or a corporate action), and the
per-form date ranges are what reveal such a shift. The other guides cover how to extract
each type once you've found it.

## Preview cheaply with `.to_context()`

Before pulling full text or large tables, print a compact summary so you understand
what's available. This saves the bulk of the tokens a raw dump would cost:

```python
print(company.to_context())
print(filings.to_context())
```

## Self-help with `.docs`

`edgartools` documents itself at runtime. When unsure of a method or attribute, query it
inline rather than guessing:

```python
company.docs                   # full API guide for the object
company.docs.search("xbrl")    # search it for a topic
latest_10k.docs.search("attachments")
```

## Inline Python preamble

When running `edgartools` inline (not via a bundled script), replicate the environment
setup the scripts do on import:

```python
import sys
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")
try:
    import truststore; truststore.inject_into_ssl()
except ImportError:
    pass
import edgar; edgar.set_identity("Jane Analyst jane@example.com")
```

This forces UTF-8 output (edgartools' emoji-rich reprs crash Windows cp1252 consoles)
and routes TLS through the OS trust store (so HTTPS works behind an inspecting corporate
proxy instead of raising `CERTIFICATE_VERIFY_FAILED`).
