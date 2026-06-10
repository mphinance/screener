"""FastAPI app: routes, static mount, CORS.

Thin HTTP layer over the shared screen pipeline (backend/pipeline.py): cache
check, delegate to run_screen, stamp cache metadata, serve the static frontend.
"""

from __future__ import annotations

import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .cache import TTLCache, make_key
from .fields import FIELDS, MARKET_FIELDS
from .models import ScreenRequest, ScreenResponse
from .pipeline import run_screen
from .presets import FACTOR_PRESETS, PRESETS
from .screener import MARKETS

app = FastAPI(title="Scanline API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache = TTLCache(ttl_seconds=20)


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
    key = make_key(req.model_dump())

    cached = _cache.get(key)
    if cached is not None:
        cached = dict(cached)
        cached["meta"] = {
            **cached["meta"],
            "cached": True,
            "ms": int((time.time() - started) * 1000),
        }
        return JSONResponse(cached)

    response = run_screen(req)
    # Only cache real results, never an upstream error response.
    if response["meta"].get("error") is None:
        _cache.set(key, response)
    return JSONResponse(response)


# Mount the static frontend at root if it exists. The frontend is built in a
# later wave, so tolerate a missing or empty folder.
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(_FRONTEND_DIR) and os.path.exists(
    os.path.join(_FRONTEND_DIR, "index.html")
):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
