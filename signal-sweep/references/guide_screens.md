# Screen Customization Guide

How to add, modify, or remove screens in `screens.json`. No Python changes needed —
the script reads the config and builds `yfinance.EquityQuery` objects dynamically.

## Screen definition format

```json
{
  "id": "my-screen",
  "name": "Human-Readable Name",
  "emoji": "📊",
  "description": "Why this screen exists and what it catches",
  "filters": [
    {"field": "some.field", "op": "gte", "value": 42}
  ],
  "sort": {"field": "some.field", "asc": true},
  "size": 25,
  "enrich": true
}
```

- **id**: unique slug, used as CLI argument (`--screen my-screen`)
- **name**: display name in output headers
- **emoji**: prefix for the output header
- **description**: shown below the header; explain the thesis behind the screen
- **filters**: list of conditions (all must pass — implicit AND)
- **sort**: which field to sort by and direction
- **size**: max results to return (default 25)
- **enrich**: whether to run the enrichment pass (adds P/E, short %, insider %, etc.)

## Filter operators

| op | Meaning | Example |
|----|---------|---------|
| `eq` | equals | `{"field": "sector", "op": "eq", "value": "Technology"}` |
| `gte` | >= | `{"field": "intradaymarketcap", "op": "gte", "value": 200000000}` |
| `lte` | <= | `{"field": "lastclose52weeklow.lasttwelvemonths", "op": "lte", "value": 1.15}` |
| `gt` | > | `{"field": "peratio.lasttwelvemonths", "op": "gt", "value": 0}` |
| `lt` | < | `{"field": "pctheldinst", "op": "lt", "value": 0.30}` |
| `btwn` | between | `{"field": "peratio.lasttwelvemonths", "op": "btwn", "value": [5, 15]}` |

## Available yfinance EquityQuery fields

### Equality fields (use with `eq`)
- `exchange` — NYSE, NMS (NASDAQ), PNK, etc.
- `sector` — Technology, Healthcare, Industrials, etc.
- `industry` — specific industry name
- `region` — "us" (always set by the universe config)
- `peer_group` — peer group identifier

### Price & return fields
- `intradaymarketcap` — current market cap in dollars
- `intradayprice` — current price
- `lastclose52weeklow.lasttwelvemonths` — ratio of last close to 52-week low (1.0 = at the low, 1.15 = 15% above)
- `lastclose52weekhigh.lasttwelvemonths` — ratio of last close to 52-week high (1.0 = at the high, 0.50 = 50% below)
- `percentchange` — intraday % change
- `fiftytwowkpercentchange` — 52-week % change (e.g. -10 means down 10%)

### Trading & ownership fields
- `pctheldinsider` — insider ownership as decimal (0.15 = 15%)
- `pctheldinst` — institutional ownership as decimal
- `beta` — beta coefficient
- `avgdailyvol3m` — 3-month average daily volume
- `dayvolume` — today's volume

### Short interest fields
- `short_percentage_of_float.value` — short % of float (15 = 15%)
- `short_interest_percentage_change.value` — % change in short interest (-20 = SI dropped 20%)
- `days_to_cover_short.value` — days to cover

### Valuation fields
- `peratio.lasttwelvemonths` — trailing P/E ratio
- `pegratio_5y` — 5-year PEG ratio
- `lastclosetevtotalrevenue.lasttwelvemonths` — EV/Revenue (trailing)
- `bookvalueshare.lasttwelvemonths` — book value per share

## Universe bounds

The `universe` section in `screens.json` is injected into every screen automatically:

```json
"universe": {
  "region": "us",
  "market_cap_min": 50000000,
  "market_cap_max": 10000000000
}
```

You don't need to repeat these in individual screen filters. To tighten the floor for
a specific screen (e.g. $200M for "fallen-from-grace"), add an `intradaymarketcap`
filter to that screen — it will override the universe floor since both conditions
must pass.

## Enrichment columns

When `"enrich": true`, the script calls `yf.Ticker(symbol).info` for each result and
adds these columns to the output:

- Analyst rating, price targets (mean, median, high, low)
- Short % of float, prior month shares short
- Insider %, institutional %
- Quarterly earnings growth, revenue growth
- Sector, industry
- Current price, market cap
- Trailing 2Y and 3Y returns (calculated from price history)

The enrichment pass takes ~1 second per ticker. For 25 results, expect ~30 seconds.
Use `--no-enrich` for faster runs when you only need the screener output.

## Example: adding a custom screen

To add a "cheap on EV/Revenue" screen:

```json
{
  "id": "cheap-ev-revenue",
  "name": "Low EV/Revenue",
  "emoji": "💰",
  "description": "Stocks trading below 1x EV/Revenue — potential value if margins expand",
  "filters": [
    {"field": "lastclosetevtotalrevenue.lasttwelvemonths", "op": "lte", "value": 1.0},
    {"field": "lastclosetevtotalrevenue.lasttwelvemonths", "op": "gt", "value": 0}
  ],
  "sort": {"field": "lastclosetevtotalrevenue.lasttwelvemonths", "asc": true},
  "size": 25,
  "enrich": true
}
```

Add this object to the `"screens"` array in `screens.json` and run:
```bash
python scripts/scan_market.py --screen cheap-ev-revenue
```
