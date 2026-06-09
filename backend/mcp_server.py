"""NEON SCREENER as an MCP server.

Exposes the exact same screen engine the web app uses (backend/pipeline.py)
over the Model Context Protocol, so any MCP client (Claude Desktop, Claude
Code, etc.) can drive the screener directly: filter, score, rank, and discover
fields across stocks, crypto, forex, futures, bonds, and CFDs.

No TradingView account needed. Data is live and delayed, same as the web app.

Run it:
    python -m backend.mcp_server              # stdio (Claude Desktop / Code)
    python -m backend.mcp_server --http 8765  # streamable-http on a port

Design notes, informed by the existing TradingView MCP servers:
  - One unified `screen` tool (our backend already spans 6 markets) plus preset
    and factor-preset runners, rather than a tool per asset class.
  - `search_fields` makes the 1000+ field universe discoverable to the model,
    the API twin of the web app's column picker.
  - Cross-field filters work out of the box: a filter value may be another
    field id, e.g. {"field":"SMA50","op":"crosses_above","value":"SMA200"}.
  - A short TTL cache in front of the engine softens TradingView's rate-limit
    cliff under bursty agent use, and `server_stats` reports on it.
"""

from __future__ import annotations

import sys
import time
from typing import Any

from fastmcp import FastMCP

from .cache import TTLCache, make_key
from .fields import CURATED_IDS, FIELDS, field_index
from .models import (
    Computed,
    Factor,
    FactorWeight,
    Filter,
    ScreenRequest,
    SortKey,
    Stat,
)
from .pipeline import run_screen
from .presets import FACTOR_PRESETS, PRESETS
from .screener import MARKETS

mcp = FastMCP("neon-screener")

# Resilience + a tiny bit of self-awareness for the stats tool.
_cache = TTLCache(ttl_seconds=20)
_STATS = {"calls": 0, "cache_hits": 0, "errors": 0, "started": time.time()}

# Operator reference, kept in lockstep with backend/screener._apply_op. The
# `value` column notes when a value may be another field id (cross-field).
OPERATORS: list[dict] = [
    {"op": ">", "value": "number or field id", "desc": "greater than"},
    {"op": ">=", "value": "number or field id", "desc": "greater than or equal"},
    {"op": "<", "value": "number or field id", "desc": "less than"},
    {"op": "<=", "value": "number or field id", "desc": "less than or equal"},
    {"op": "==", "value": "number, string, or field id", "desc": "equal"},
    {"op": "!=", "value": "number, string, or field id", "desc": "not equal"},
    {"op": "between", "value": "[low, high]", "desc": "inclusive range"},
    {"op": "not_between", "value": "[low, high]", "desc": "outside a range"},
    {"op": "above_pct", "value": "[field id, fraction]", "desc": "within fraction below a field, e.g. close above_pct [price_52_week_high, 0.95]"},
    {"op": "below_pct", "value": "[field id, fraction]", "desc": "within fraction above a field"},
    {"op": "crosses", "value": "number or field id", "desc": "crossed in either direction this bar"},
    {"op": "crosses_above", "value": "number or field id", "desc": "crossed up through (golden-cross style)"},
    {"op": "crosses_below", "value": "number or field id", "desc": "crossed down through (death-cross style)"},
    {"op": "isin", "value": "[v1, v2, ...]", "desc": "value is one of"},
    {"op": "not_in", "value": "[v1, v2, ...]", "desc": "value is none of"},
    {"op": "in_day_range", "value": "[low, high]", "desc": "today's range overlaps"},
    {"op": "in_week_range", "value": "[low, high]", "desc": "this week's range overlaps"},
    {"op": "in_month_range", "value": "[low, high]", "desc": "this month's range overlaps"},
    {"op": "like", "value": "substring", "desc": "text contains"},
    {"op": "not_like", "value": "substring", "desc": "text does not contain"},
    {"op": "empty", "value": "(none)", "desc": "field has no value"},
    {"op": "not_empty", "value": "(none)", "desc": "field has a value"},
]


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _render_table(columns: list[str], rows: list[dict], max_rows: int = 50) -> str:
    """Render rows as an aligned monospace table, token-efficient for the model."""
    if not rows:
        return "(no rows)"
    cols = columns or list(rows[0].keys())
    shown = rows[:max_rows]

    def cell(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, float):
            return f"{v:,.4g}" if abs(v) < 1e6 else f"{v:,.0f}"
        return str(v)

    widths = {c: len(c) for c in cols}
    table_cells = []
    for r in shown:
        row_cells = {c: cell(r.get(c)) for c in cols}
        for c in cols:
            widths[c] = max(widths[c], len(row_cells[c]))
        table_cells.append(row_cells)

    header = "  ".join(c.ljust(widths[c]) for c in cols)
    sep = "  ".join("-" * widths[c] for c in cols)
    body = "\n".join(
        "  ".join(rc[c].ljust(widths[c]) for c in cols) for rc in table_cells
    )
    extra = f"\n... {len(rows) - max_rows} more rows" if len(rows) > max_rows else ""
    return f"{header}\n{sep}\n{body}{extra}"


def _shape(resp: dict, table_rows: int = 50) -> dict:
    """Add a rendered table and a one-line summary to a pipeline response."""
    meta = resp.get("meta", {})
    if meta.get("error"):
        _STATS["errors"] += 1
        return {
            "error": meta["error"],
            "market": meta.get("market"),
            "count": 0,
            "rows": [],
        }
    rows, columns = resp["rows"], resp["columns"]
    return {
        "count": resp["count"],
        "returned": len(rows),
        "market": meta.get("market"),
        "ms": meta.get("ms"),
        "columns": columns,
        "rows": rows,
        "table": _render_table(columns, rows, max_rows=table_rows),
    }


def _run(req: ScreenRequest, table_rows: int = 50) -> dict:
    """Run a screen through the cache and shape it for the model."""
    _STATS["calls"] += 1
    key = make_key(req.model_dump())
    cached = _cache.get(key)
    if cached is not None:
        _STATS["cache_hits"] += 1
        return _shape(cached, table_rows)
    resp = run_screen(req)
    if resp["meta"].get("error") is None:
        _cache.set(key, resp)
    return _shape(resp, table_rows)


# ----------------------------------------------------------------------------
# Discovery tools
# ----------------------------------------------------------------------------
@mcp.tool
def list_markets() -> list[dict]:
    """List the markets the screener can target.

    Returns each market's id (use as the `market` arg elsewhere), a label, and
    its kind. Covers US stocks, crypto, forex, futures, bonds, and CFDs.
    """
    return MARKETS


@mcp.tool
def search_fields(query: str = "", group: str = "", limit: int = 40) -> dict:
    """Search the TradingView field universe (1000+ fields) by id, label, or group.

    This is how you discover what you can filter, sort, and select on. The
    curated set (price, performance, valuation, profitability, dividends,
    technicals, moving averages, oscillators, volume, volatility) leads; every
    other queryable base field is reachable too.

    query: case-insensitive substring matched against field id and label.
    group: optional exact group filter, e.g. "Oscillators", "Valuation".
    Returns {count, fields:[{id,label,group,type,unit,curated}]}.
    """
    q = query.strip().lower()
    g = group.strip().lower()
    out: list[dict] = []
    for f in FIELDS:
        if g and f["group"].lower() != g:
            continue
        if q and q not in f["id"].lower() and q not in f["label"].lower():
            continue
        out.append({**f, "curated": f["id"] in CURATED_IDS})
        if len(out) >= max(1, limit):
            break
    return {"count": len(out), "fields": out}


@mcp.tool
def list_operators() -> list[dict]:
    """List the filter operators, what value each expects, and what it means.

    Note the cross-field operators: a value may be another field id, so
    {"field":"SMA50","op":"crosses_above","value":"SMA200"} is a golden cross
    and {"field":"close","op":">","value":"VWAP"} is price over VWAP.
    """
    return OPERATORS


@mcp.tool
def list_presets(group: str = "") -> list[dict]:
    """List the one-click preset scans (id, name, description, market, group).

    47 presets across general scans and the SIGNALS / MOMENTUM / TREND /
    MULTI-TIMEFRAME signal groups. Pass `group` to filter, e.g. "Momentum".
    Run one with `run_preset`.
    """
    g = group.strip().lower()
    out = []
    for p in PRESETS:
        if g and p.get("group", "").lower() != g:
            continue
        out.append(
            {
                "id": p["id"],
                "name": p["name"],
                "description": p["description"],
                "market": p["market"],
                "group": p.get("group", "General"),
            }
        )
    return out


@mcp.tool
def list_factor_presets() -> list[dict]:
    """List the composite factor-scoring presets (Momentum, Value, Quality, ...).

    Each is a weighted, direction-aware blend of fields. Run one with
    `run_factor_preset` to rank a market by that factor.
    """
    return [
        {"id": fp["id"], "name": fp["name"], "weights": fp["weights"]}
        for fp in FACTOR_PRESETS
    ]


# ----------------------------------------------------------------------------
# The core screen tool
# ----------------------------------------------------------------------------
@mcp.tool
def screen(
    market: str = "america",
    filters: list[dict] | None = None,
    columns: list[str] | None = None,
    match: str = "all",
    sort: list[dict] | None = None,
    computed: list[dict] | None = None,
    stats: list[dict] | None = None,
    factor: list[dict] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Run a live market screen and return the matching rows.

    This is the full engine the web app uses, including the analytics layer that
    makes this more than a filter.

    market:  one of list_markets() ids (america, crypto, forex, futures, bond, cfd).
    filters: list of {"field","op","value"}. See list_operators(). Values may be
             numbers, strings, lists, or another field id (cross-field). Example:
             [{"field":"market_cap_basic","op":">","value":1e9},
              {"field":"RSI","op":"<","value":30}]
    columns: field ids to select (see search_fields). Defaults to a sensible set.
    match:   "all" (AND) or "any" (OR) across filters.
    sort:    list of {"field","dir"} with dir "asc"|"desc". First key is applied
             server-side; you may sort by a computed/stat/factor column too.
    computed: derived columns via a sandboxed expression engine, e.g.
             [{"id":"dollar_vol","expr":"close*volume"},
              {"id":"range_pct","expr":"(high-low)/close*100"}].
             Operators + - * / % ** and abs min max round sqrt log ln floor ceil.
    stats:   in-result statistics computed across the returned set, e.g.
             [{"fn":"zscore","field":"change"},{"fn":"pctrank","field":"volume"}].
             fn is one of zscore | pctrank | rank | norm. Column name is "fn(field)".
    factor:  composite factor score: list of {"field","weight","dir"} with dir
             "high"|"low". Adds a "factor_score" column and ranks by it when no
             explicit sort is given.
    limit:   max rows (default 50). offset: skip N rows for paging.

    Returns {count, returned, market, ms, columns, rows, table}. `count` is the
    full universe size matching the filters; `rows` is the page you asked for.
    """
    factor_model = None
    if factor:
        factor_model = Factor(weights=[FactorWeight(**w) for w in factor])
    req = ScreenRequest(
        market=market,
        filters=[Filter(**f) for f in (filters or [])],
        columns=columns or [],
        match=match,
        sort=[SortKey(**s) for s in (sort or [])],
        computed=[Computed(**c) for c in (computed or [])],
        stats=[Stat(**s) for s in (stats or [])],
        factor=factor_model,
        limit=limit,
        offset=offset,
    )
    return _run(req, table_rows=min(limit, 50))


@mcp.tool
def run_preset(preset_id: str, limit: int = 50) -> dict:
    """Run a named preset scan (see list_presets) and return its rows.

    The preset supplies the market, filters, columns, and sort. `limit` caps
    the rows returned.
    """
    preset = next((p for p in PRESETS if p["id"] == preset_id), None)
    if preset is None:
        return {"error": f"Unknown preset: {preset_id}. See list_presets()."}
    req = ScreenRequest(
        market=preset["market"],
        filters=[Filter(**f) for f in preset.get("filters", [])],
        columns=preset.get("columns", []),
        match=preset.get("match", "all"),
        sort=[SortKey(**s) for s in preset.get("sort", [])],
        limit=limit,
    )
    return _run(req, table_rows=min(limit, 50))


@mcp.tool
def run_factor_preset(
    factor_preset_id: str,
    market: str = "america",
    filters: list[dict] | None = None,
    columns: list[str] | None = None,
    limit: int = 50,
) -> dict:
    """Rank a market by a named composite factor (see list_factor_presets).

    Applies the factor's weighted, direction-aware z-score blend, adds a
    "factor_score" column, and ranks by it. Narrow the universe first with
    `filters` (recommended, e.g. a market-cap floor) so the ranking is over a
    meaningful set.
    """
    fp = next((f for f in FACTOR_PRESETS if f["id"] == factor_preset_id), None)
    if fp is None:
        return {"error": f"Unknown factor preset: {factor_preset_id}. See list_factor_presets()."}
    req = ScreenRequest(
        market=market,
        filters=[Filter(**f) for f in (filters or [])],
        columns=columns or [],
        factor=Factor(weights=[FactorWeight(**w) for w in fp["weights"]]),
        limit=limit,
    )
    return _run(req, table_rows=min(limit, 50))


@mcp.tool
def lookup_symbol(ticker: str, market: str = "america", columns: list[str] | None = None) -> dict:
    """Fetch one symbol's row by ticker (e.g. "NVDA", "BTCUSD").

    Matches case-insensitively on the `name` field. Returns the single row with
    the requested columns (or a broad default set), or an error if not found.
    """
    cols = columns or [
        "name", "description", "close", "change", "volume", "market_cap_basic",
        "RSI", "Perf.1M", "Perf.YTD", "price_earnings_ttm", "sector",
    ]
    cols = [c for c in cols if c in field_index]
    req = ScreenRequest(
        market=market,
        filters=[Filter(field="name", op="==", value=ticker.upper())],
        columns=cols,
        limit=1,
    )
    out = _run(req, table_rows=1)
    if out.get("rows"):
        return {"symbol": ticker.upper(), "market": market, "row": out["rows"][0], "table": out["table"]}
    if out.get("error"):
        return out
    return {"error": f"No symbol '{ticker.upper()}' found in market '{market}'."}


@mcp.tool
def server_stats() -> dict:
    """Report screener MCP server health: calls served, cache hit rate, errors.

    A self-monitoring tool, handy for confirming the cache is doing its job and
    that upstream calls are healthy.
    """
    uptime = time.time() - _STATS["started"]
    calls = _STATS["calls"]
    return {
        "uptime_seconds": int(uptime),
        "screen_calls": calls,
        "cache_hits": _STATS["cache_hits"],
        "cache_hit_rate": round(_STATS["cache_hits"] / calls, 3) if calls else 0.0,
        "errors": _STATS["errors"],
        "cache_ttl_seconds": _cache.ttl,
        "fields_indexed": len(FIELDS),
        "presets": len(PRESETS),
        "factor_presets": len(FACTOR_PRESETS),
        "markets": len(MARKETS),
    }


# ----------------------------------------------------------------------------
# Resources: catalogs the model can read wholesale
# ----------------------------------------------------------------------------
@mcp.resource("screener://fields")
def fields_resource() -> dict:
    """The full field catalog (id, label, group, type, unit)."""
    return {"count": len(FIELDS), "fields": FIELDS}


@mcp.resource("screener://presets")
def presets_resource() -> dict:
    """Every preset scan and factor preset, in full."""
    return {"presets": PRESETS, "factor_presets": FACTOR_PRESETS}


@mcp.resource("screener://operators")
def operators_resource() -> list[dict]:
    """The filter operator reference."""
    return OPERATORS


def main() -> None:
    """Entry point. Default stdio; `--http PORT` for streamable-http."""
    args = sys.argv[1:]
    if "--http" in args:
        i = args.index("--http")
        port = int(args[i + 1]) if i + 1 < len(args) else 8765
        mcp.run(transport="http", port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
