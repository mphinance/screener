"""One-click preset scans and factor-scoring presets.

PRESETS use real field ids and the op strings backend/screener.py understands.
FACTOR_PRESETS feed backend/analytics.apply_factor.
"""

from __future__ import annotations

# Column sets reused across several presets.
_CORE = ["name", "description", "close", "change", "volume", "market_cap_basic"]
_TECH = ["name", "close", "change", "RSI", "volume", "relative_volume_10d_calc"]
_FUND = ["name", "description", "close", "market_cap_basic", "price_earnings_ttm", "return_on_equity"]


PRESETS: list[dict] = [
    {
        "id": "top_gainers",
        "name": "Top Gainers",
        "description": "Biggest percentage movers up today, liquid names only.",
        "market": "america",
        "columns": _CORE + ["relative_volume_10d_calc"],
        "filters": [
            {"field": "market_cap_basic", "op": ">", "value": 1e8},
            {"field": "volume", "op": ">", "value": 200000},
        ],
        "match": "all",
        "sort": [{"field": "change", "dir": "desc"}],
    },
    {
        "id": "top_losers",
        "name": "Top Losers",
        "description": "Biggest percentage movers down today, liquid names only.",
        "market": "america",
        "columns": _CORE + ["relative_volume_10d_calc"],
        "filters": [
            {"field": "market_cap_basic", "op": ">", "value": 1e8},
            {"field": "volume", "op": ">", "value": 200000},
        ],
        "match": "all",
        "sort": [{"field": "change", "dir": "asc"}],
    },
    {
        "id": "unusual_volume",
        "name": "Unusual Volume",
        "description": "Relative volume well above the 10-day average.",
        "market": "america",
        "columns": _CORE + ["relative_volume_10d_calc", "average_volume_10d_calc"],
        "filters": [
            {"field": "relative_volume_10d_calc", "op": ">", "value": 3},
            {"field": "market_cap_basic", "op": ">", "value": 1e8},
        ],
        "match": "all",
        "sort": [{"field": "relative_volume_10d_calc", "dir": "desc"}],
    },
    {
        "id": "rsi_oversold",
        "name": "RSI Oversold",
        "description": "RSI under 30, potential mean-reversion candidates.",
        "market": "america",
        "columns": _TECH,
        "filters": [
            {"field": "RSI", "op": "<", "value": 30},
            {"field": "market_cap_basic", "op": ">", "value": 3e8},
        ],
        "match": "all",
        "sort": [{"field": "RSI", "dir": "asc"}],
    },
    {
        "id": "rsi_overbought",
        "name": "RSI Overbought",
        "description": "RSI above 70, stretched to the upside.",
        "market": "america",
        "columns": _TECH,
        "filters": [
            {"field": "RSI", "op": ">", "value": 70},
            {"field": "market_cap_basic", "op": ">", "value": 3e8},
        ],
        "match": "all",
        "sort": [{"field": "RSI", "dir": "desc"}],
    },
    {
        "id": "high_52w",
        "name": "52-Week Highs",
        "description": "Trading at or very near the 52-week high.",
        "market": "america",
        "columns": _CORE + ["price_52_week_high", "Perf.Y"],
        "filters": [
            {"field": "close", "op": "above_pct", "value": ["price_52_week_high", 0.98]},
            {"field": "market_cap_basic", "op": ">", "value": 3e8},
        ],
        "match": "all",
        "sort": [{"field": "Perf.Y", "dir": "desc"}],
    },
    {
        "id": "low_52w",
        "name": "52-Week Lows",
        "description": "Trading at or very near the 52-week low.",
        "market": "america",
        "columns": _CORE + ["price_52_week_low", "Perf.Y"],
        "filters": [
            {"field": "close", "op": "below_pct", "value": ["price_52_week_low", 0.02]},
            {"field": "market_cap_basic", "op": ">", "value": 3e8},
        ],
        "match": "all",
        "sort": [{"field": "Perf.Y", "dir": "asc"}],
    },
    {
        "id": "gap_ups",
        "name": "Gap Ups",
        "description": "Opened with a sizable gap higher on volume.",
        "market": "america",
        "columns": _CORE + ["gap", "relative_volume_10d_calc"],
        "filters": [
            {"field": "gap", "op": ">", "value": 3},
            {"field": "market_cap_basic", "op": ">", "value": 1e8},
        ],
        "match": "all",
        "sort": [{"field": "gap", "dir": "desc"}],
    },
    {
        "id": "golden_cross",
        "name": "Golden Cross",
        "description": "Price above SMA50 and SMA50 above SMA200, uptrend stack.",
        "market": "america",
        "columns": _CORE + ["SMA50", "SMA200"],
        "filters": [
            {"field": "close", "op": ">", "value": "SMA50"},
            {"field": "SMA50", "op": ">", "value": "SMA200"},
            {"field": "market_cap_basic", "op": ">", "value": 3e8},
        ],
        "match": "all",
        "sort": [{"field": "Perf.3M", "dir": "desc"}],
    },
    {
        "id": "death_cross",
        "name": "Death Cross",
        "description": "Price below SMA50 and SMA50 below SMA200, downtrend stack.",
        "market": "america",
        "columns": _CORE + ["SMA50", "SMA200"],
        "filters": [
            {"field": "close", "op": "<", "value": "SMA50"},
            {"field": "SMA50", "op": "<", "value": "SMA200"},
            {"field": "market_cap_basic", "op": ">", "value": 3e8},
        ],
        "match": "all",
        "sort": [{"field": "Perf.3M", "dir": "asc"}],
    },
    {
        "id": "high_short_interest",
        "name": "High Short Interest",
        "description": "Heavily shorted as a percent of float, squeeze watch.",
        "market": "america",
        "columns": _CORE + ["short_interest_percent_of_float", "relative_volume_10d_calc"],
        "filters": [
            {"field": "short_interest_percent_of_float", "op": ">", "value": 15},
            {"field": "market_cap_basic", "op": ">", "value": 3e8},
        ],
        "match": "all",
        "sort": [{"field": "short_interest_percent_of_float", "dir": "desc"}],
    },
    {
        "id": "dividend_aristocrats",
        "name": "Dividend Aristocrats",
        "description": "Solid yield with a sustainable payout ratio.",
        "market": "america",
        "columns": _FUND + ["dividend_yield_recent", "payout_ratio"],
        "filters": [
            {"field": "dividend_yield_recent", "op": ">", "value": 3},
            {"field": "payout_ratio", "op": "between", "value": [10, 80]},
            {"field": "market_cap_basic", "op": ">", "value": 2e9},
        ],
        "match": "all",
        "sort": [{"field": "dividend_yield_recent", "dir": "desc"}],
    },
    {
        "id": "mega_cap_movers",
        "name": "Mega Cap Movers",
        "description": "The largest companies making the biggest moves today.",
        "market": "america",
        "columns": _CORE + ["Perf.W"],
        "filters": [
            {"field": "market_cap_basic", "op": ">", "value": 1e11},
        ],
        "match": "all",
        "sort": [{"field": "change", "dir": "desc"}],
    },
    {
        "id": "small_cap_momentum",
        "name": "Small Cap Momentum",
        "description": "Small caps with strong recent momentum and volume.",
        "market": "america",
        "columns": _CORE + ["Perf.1M", "relative_volume_10d_calc"],
        "filters": [
            {"field": "market_cap_basic", "op": "between", "value": [3e8, 2e9]},
            {"field": "Perf.1M", "op": ">", "value": 15},
            {"field": "relative_volume_10d_calc", "op": ">", "value": 1.5},
        ],
        "match": "all",
        "sort": [{"field": "Perf.1M", "dir": "desc"}],
    },
    {
        "id": "value_plays",
        "name": "Value Plays",
        "description": "Low P/E with positive return on equity.",
        "market": "america",
        "columns": _FUND + ["price_book_fq", "debt_to_equity"],
        "filters": [
            {"field": "price_earnings_ttm", "op": "between", "value": [0, 15]},
            {"field": "return_on_equity", "op": ">", "value": 10},
            {"field": "market_cap_basic", "op": ">", "value": 1e9},
        ],
        "match": "all",
        "sort": [{"field": "price_earnings_ttm", "dir": "asc"}],
    },
    {
        "id": "breakouts",
        "name": "Breakouts",
        "description": "Near the 52-week high on elevated relative volume.",
        "market": "america",
        "columns": _CORE + ["price_52_week_high", "relative_volume_10d_calc"],
        "filters": [
            {"field": "close", "op": "above_pct", "value": ["price_52_week_high", 0.95]},
            {"field": "relative_volume_10d_calc", "op": ">", "value": 2},
            {"field": "market_cap_basic", "op": ">", "value": 3e8},
        ],
        "match": "all",
        "sort": [{"field": "relative_volume_10d_calc", "dir": "desc"}],
    },
    {
        "id": "high_beta",
        "name": "High Beta",
        "description": "Most volatile names relative to the market.",
        "market": "america",
        "columns": _CORE + ["beta_1_year", "Volatility.D"],
        "filters": [
            {"field": "beta_1_year", "op": ">", "value": 2},
            {"field": "market_cap_basic", "op": ">", "value": 1e9},
        ],
        "match": "all",
        "sort": [{"field": "beta_1_year", "dir": "desc"}],
    },
    {
        "id": "low_volatility",
        "name": "Low Volatility",
        "description": "Large caps with the calmest daily ranges.",
        "market": "america",
        "columns": _CORE + ["beta_1_year", "Volatility.D"],
        "filters": [
            {"field": "beta_1_year", "op": "between", "value": [0, 0.8]},
            {"field": "market_cap_basic", "op": ">", "value": 1e10},
        ],
        "match": "all",
        "sort": [{"field": "Volatility.D", "dir": "asc"}],
    },
    {
        "id": "oversold_megacaps",
        "name": "Oversold MegaCaps",
        "description": "Giant companies with RSI in oversold territory.",
        "market": "america",
        "columns": _CORE + ["RSI", "Perf.1M"],
        "filters": [
            {"field": "RSI", "op": "<", "value": 40},
            {"field": "market_cap_basic", "op": ">", "value": 5e10},
        ],
        "match": "all",
        "sort": [{"field": "RSI", "dir": "asc"}],
    },
    {
        "id": "crypto_movers",
        "name": "Crypto Movers",
        "description": "Biggest crypto movers by 24h change.",
        "market": "crypto",
        "columns": ["name", "close", "change", "volume", "market_cap_calc", "Value.Traded"],
        "filters": [
            {"field": "Value.Traded", "op": ">", "value": 1e6},
        ],
        "match": "all",
        "sort": [{"field": "change", "dir": "desc"}],
    },
    {
        "id": "most_active",
        "name": "Most Active",
        "description": "Highest dollar volume traded today.",
        "market": "america",
        "columns": _CORE + ["Value.Traded", "relative_volume_10d_calc"],
        "filters": [
            {"field": "market_cap_basic", "op": ">", "value": 1e8},
        ],
        "match": "all",
        "sort": [{"field": "volume", "dir": "desc"}],
    },
    {
        "id": "earnings_quality",
        "name": "Earnings Quality",
        "description": "High return on equity with healthy margins.",
        "market": "america",
        "columns": _FUND + ["net_margin", "operating_margin"],
        "filters": [
            {"field": "return_on_equity", "op": ">", "value": 20},
            {"field": "net_margin", "op": ">", "value": 10},
            {"field": "market_cap_basic", "op": ">", "value": 2e9},
        ],
        "match": "all",
        "sort": [{"field": "return_on_equity", "dir": "desc"}],
    },
]


FACTOR_PRESETS: list[dict] = [
    {
        "id": "momentum",
        "name": "Momentum",
        "weights": [
            {"field": "Perf.1M", "weight": 1.0, "dir": "high"},
            {"field": "Perf.3M", "weight": 1.0, "dir": "high"},
            {"field": "Perf.6M", "weight": 0.5, "dir": "high"},
            {"field": "relative_volume_10d_calc", "weight": 0.5, "dir": "high"},
        ],
    },
    {
        "id": "value",
        "name": "Value",
        "weights": [
            {"field": "price_earnings_ttm", "weight": 1.0, "dir": "low"},
            {"field": "price_book_fq", "weight": 1.0, "dir": "low"},
            {"field": "price_sales_current", "weight": 0.5, "dir": "low"},
            {"field": "dividend_yield_recent", "weight": 0.5, "dir": "high"},
        ],
    },
    {
        "id": "quality",
        "name": "Quality",
        "weights": [
            {"field": "return_on_equity", "weight": 1.0, "dir": "high"},
            {"field": "return_on_invested_capital", "weight": 1.0, "dir": "high"},
            {"field": "net_margin", "weight": 0.5, "dir": "high"},
            {"field": "debt_to_equity", "weight": 0.5, "dir": "low"},
        ],
    },
    {
        "id": "growth",
        "name": "Growth",
        "weights": [
            {"field": "revenue_growth_ttm_yoy", "weight": 1.0, "dir": "high"},
            {"field": "earnings_per_share_diluted_growth_percent_ttm_yoy", "weight": 1.0, "dir": "high"},
            {"field": "gross_margin", "weight": 0.5, "dir": "high"},
        ],
    },
    {
        "id": "low_vol",
        "name": "Low-Vol",
        "weights": [
            {"field": "beta_1_year", "weight": 1.0, "dir": "low"},
            {"field": "Volatility.D", "weight": 1.0, "dir": "low"},
            {"field": "Volatility.M", "weight": 0.5, "dir": "low"},
        ],
    },
]
