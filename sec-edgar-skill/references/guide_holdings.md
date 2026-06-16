# Holdings — deep route (edgartools) and blockholders (13D/13G)

> **For the common case** — "who owns this stock?", "how has ownership changed?",
> "what does this fund hold?" — use `scripts/fetch_13f_holders.py` directly.
> It is already listed in the Scripts section of SKILL.md and needs no guide.
> Read this file only when you need **raw 13F filing data** (voting authority,
> amendments, specific holding details) or **blockholder schedules** (13D/13G).

## Raw 13F via edgartools

13F is filed by the **investment manager**, not the operating company. Query the manager:

```python
manager = Company("Magnetar Capital LLC")
f13 = manager.get_filings(form="13F-HR").latest().obj()
df = f13.holdings                          # the holdings DataFrame
```

> Operating companies (AAPL, etc.) do **not** file 13F — querying their CIK for `13F-HR`
> returns an empty collection. You must query the fund manager's name or CIK.
>
> Holdings live on the `.holdings` attribute; the 13F object has no `.to_dataframe()`.

Filter the holdings DataFrame by CUSIP or issuer name to confirm whether a given manager
holds a target stock (you query each manager you care about).

## Blockholders (Schedules 13D / 13G)

13D signals an active/control intent; 13G signals a passive stake. Query both, and
include the `"SC "`-prefixed names — EDGAR often indexes these schedules that way, so
omitting them returns empty results:

```python
blocks = company.get_filings(
    form=["13D", "13G", "SC 13D", "SC 13G", "SC 13D/A", "SC 13G/A"]
)
sched = blocks.latest().obj()        # Schedule13D / Schedule13G structured object
sched.reporting_persons              # who holds — each with voting / dispositive power
sched.issuer_info                    # the subject company (name, CIK, CUSIP)
sched.total_percent                  # aggregate % of class
sched.items.item4_purpose_of_transaction   # 13D Item 4 narrative, when present
```

These schedules parse into a **structured object**, not an item-addressable one — there is
no `sched["Item 4"]`. The per-item values live on `sched.items` (a dataclass with fields
like `item4_purpose_of_transaction` and `item5_percentage_of_class`).

> **Older filings lack structured tags.** Before EDGAR's late-2024 structured-XML mandate,
> `sched.has_structured_data` is `False` and the parsed fields come back `None`/`0`. For
> those, save the full Markdown (`fetch_filing.py`, no `--section`) and grep the ownership
> figure and the Item 4 purpose out of the text instead.
