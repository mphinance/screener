"""FastAPI app: routes, static mount, CORS.

Orchestrates the screen pipeline: cache check, run query, computed columns,
stats, factor scoring, optional re-sort, response shaping.
"""

from __future__ import annotations

import math
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import analytics, screener
from .cache import TTLCache, make_key
from .fields import FIELDS, MARKET_FIELDS, default_columns
from .models import ScreenRequest, ScreenResponse
from .presets import FACTOR_PRESETS, PRESETS
from .screener import MARKETS, ScreenerError, run_query

app = FastAPI(title="Neon Screener API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache = TTLCache(ttl_seconds=20)


def _round_floats(rows: list[dict]) -> list[dict]:
    """Round floats to a reasonable display precision, drop NaN/inf."""
    for row in rows:
        for k, v in row.items():
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    row[k] = None
                else:
                    row[k] = round(v, 6)
    return rows


@app.get("/api/health")
def health() -> dict:
    """Liveness and catalog sizes."""
    return {
        "ok": True,
        "markets": len(MARKETS),
        "fields": len(FIELDS),
        "presets": len(PRESETS),
        "factor_presets": len(FACTOR_PRESETS),
    }


@app.get("/api/markets")
def markets() -> list[dict]:
    """Available markets."""
    return MARKETS


@app.get("/api/fields")
def fields() -> dict:
    """The field catalog plus per-market relevance hints."""
    return {"fields": FIELDS, "market_fields": MARKET_FIELDS}


@app.get("/api/presets")
def presets() -> dict:
    """Preset scans and factor-scoring presets."""
    return {"presets": PRESETS, "factor_presets": FACTOR_PRESETS}


@app.get("/api/factor-presets")
def factor_presets() -> list[dict]:
    """Factor-scoring presets only."""
    return FACTOR_PRESETS


@app.post("/api/screen", response_model=ScreenResponse)
def screen(req: ScreenRequest) -> JSONResponse:
    """Run the full screen pipeline and return shaped results."""
    started = time.time()
    payload = req.model_dump()
    key = make_key(payload)

    cached = _cache.get(key)
    if cached is not None:
        cached = dict(cached)
        cached["meta"] = {
            **cached["meta"],
            "cached": True,
            "ms": int((time.time() - started) * 1000),
        }
        return JSONResponse(cached)

    # Build the column set for the query: requested columns plus any base
    # fields the stats and factor steps need to read.
    base_columns = list(req.columns) or default_columns(req.market)
    needed = set(base_columns)
    for s in req.stats:
        needed.add(s.field)
    if req.factor:
        for w in req.factor.weights:
            needed.add(w.field)
    # Sort on a base (non-derived) field needs that column present too.
    derived_ids = {c.id for c in req.computed} | {"factor_score"}
    for sk in req.sort:
        if sk.field not in derived_ids and not sk.field.startswith(
            ("zscore(", "pctrank(", "rank(", "norm(")
        ):
            needed.add(sk.field)

    query_columns = list(dict.fromkeys([*base_columns, *needed]))

    try:
        result = run_query(
            market=req.market,
            columns=query_columns,
            filters=[f.model_dump() for f in req.filters],
            match=req.match,
            sort=[s.model_dump() for s in req.sort] or None,
            limit=req.limit,
            offset=req.offset,
        )
    except ScreenerError as exc:
        return JSONResponse(
            {
                "count": 0,
                "rows": [],
                "columns": [],
                "meta": {
                    "cached": False,
                    "ms": int((time.time() - started) * 1000),
                    "market": req.market,
                    "error": str(exc),
                },
            }
        )

    rows = result["rows"]

    # Analytics pipeline over the returned rows.
    if req.computed:
        rows = analytics.apply_computed(rows, [c.model_dump() for c in req.computed])
    if req.stats:
        rows = analytics.apply_stats(rows, [s.model_dump() for s in req.stats])

    factor_requested = bool(req.factor and req.factor.weights)
    if factor_requested:
        rows = analytics.apply_factor(
            rows, [w.model_dump() for w in req.factor.weights]
        )
        # Re-sort by factor_score when the caller gave no explicit sort.
        if not req.sort:
            rows.sort(key=lambda r: r.get("factor_score") or float("-inf"), reverse=True)

    rows = _round_floats(rows)

    # Final ordered column list: query columns, then computed, stats, factor.
    ordered: list[str] = []
    for c in result["columns"]:
        if c not in ordered:
            ordered.append(c)
    for c in req.computed:
        if c.id not in ordered:
            ordered.append(c.id)
    for s in req.stats:
        name = f"{s.fn}({s.field})"
        if name not in ordered:
            ordered.append(name)
    if factor_requested and "factor_score" not in ordered:
        ordered.append("factor_score")

    response = {
        "count": result["count"],
        "rows": rows,
        "columns": ordered,
        "meta": {
            "cached": False,
            "ms": int((time.time() - started) * 1000),
            "market": req.market,
            "error": None,
        },
    }
    _cache.set(key, response)
    return JSONResponse(response)


# Mount the static frontend at root if it exists. The frontend is built in a
# later wave, so tolerate a missing or empty folder.
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(_FRONTEND_DIR) and os.path.exists(
    os.path.join(_FRONTEND_DIR, "index.html")
):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
