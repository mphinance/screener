"""MCP server tests.

The discovery tools and resources run fully offline (they read the catalog and
preset tables, no network). The screen path is marked 'live' since it hits the
real tradingview endpoint. Each test drives the server through fastmcp's
in-memory Client, exactly as a real MCP client would.
"""

from __future__ import annotations

import asyncio

import pytest
from fastmcp import Client

from backend.mcp_server import mcp


def _call(name: str, args: dict | None = None):
    """Run one MCP tool call through an in-memory client and return its data."""

    async def run():
        async with Client(mcp) as c:
            res = await c.call_tool(name, args or {})
            return res.data

    return asyncio.run(run())


def _list():
    async def run():
        async with Client(mcp) as c:
            tools = [t.name for t in await c.list_tools()]
            resources = [str(r.uri) for r in await c.list_resources()]
            return tools, resources

    return asyncio.run(run())


# --- wiring --------------------------------------------------------------

def test_tools_and_resources_registered():
    tools, resources = _list()
    expected_tools = {
        "list_markets", "search_fields", "list_operators", "list_presets",
        "list_factor_presets", "screen", "run_preset", "run_factor_preset",
        "lookup_symbol", "server_stats",
    }
    assert expected_tools <= set(tools)
    assert {"screener://fields", "screener://presets", "screener://operators"} <= set(resources)


# --- discovery (offline) -------------------------------------------------

def test_list_markets():
    markets = _call("list_markets")
    ids = {m["id"] for m in markets}
    assert {"america", "crypto", "forex", "futures", "bond", "cfd"} <= ids


def test_search_fields_finds_rsi():
    out = _call("search_fields", {"query": "rsi", "limit": 10})
    ids = {f["id"] for f in out["fields"]}
    assert "RSI" in ids
    assert out["count"] <= 10
    assert all("curated" in f for f in out["fields"])


def test_search_fields_group_filter():
    out = _call("search_fields", {"group": "Oscillators", "limit": 100})
    assert out["count"] > 0
    assert all(f["group"] == "Oscillators" for f in out["fields"])


def test_list_operators_includes_cross_field():
    ops = {o["op"] for o in _call("list_operators")}
    assert {"crosses_above", "crosses_below", "between", "above_pct"} <= ops


def test_list_presets_and_group_filter():
    allp = _call("list_presets")
    assert len(allp) >= 22
    momentum = _call("list_presets", {"group": "Momentum"})
    assert len(momentum) > 0
    assert all(p["group"] == "Momentum" for p in momentum)


def test_list_factor_presets():
    fps = _call("list_factor_presets")
    ids = {f["id"] for f in fps}
    assert {"momentum", "value", "quality", "growth", "low_vol"} <= ids


def test_server_stats_shape():
    s = _call("server_stats")
    assert s["markets"] == 6
    assert s["fields_indexed"] > 150
    assert "cache_hit_rate" in s


# --- error paths (offline) ----------------------------------------------

def test_run_preset_unknown_id():
    out = _call("run_preset", {"preset_id": "does_not_exist"})
    assert "error" in out


def test_run_factor_preset_unknown_id():
    out = _call("run_factor_preset", {"factor_preset_id": "does_not_exist"})
    assert "error" in out


# --- live screen path ----------------------------------------------------

@pytest.mark.live
def test_screen_live_with_analytics():
    out = _call("screen", {
        "market": "america",
        "filters": [{"field": "market_cap_basic", "op": ">", "value": 1e10}],
        "columns": ["name", "close", "change", "volume"],
        "computed": [{"id": "dollar_vol", "expr": "close*volume"}],
        "stats": [{"fn": "zscore", "field": "change"}],
        "sort": [{"field": "volume", "dir": "desc"}],
        "limit": 5,
    })
    assert out["count"] > 0
    assert out["returned"] <= 5
    assert "dollar_vol" in out["columns"]
    assert "zscore(change)" in out["columns"]
    assert out["table"]


@pytest.mark.live
def test_lookup_symbol_live():
    out = _call("lookup_symbol", {"ticker": "AAPL"})
    assert out.get("row", {}).get("name") == "AAPL"
