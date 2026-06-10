# MCP reference

The NEON SCREENER MCP server (`backend/mcp_server.py`) exposes the live screen
engine over the Model Context Protocol so any MCP client can screen, score,
rank, and read charts. Built on `fastmcp`. Pure TradingView data, no account
needed (data is live and delayed).

## Run

```bash
python run_mcp.py              # stdio (Claude Desktop, Claude Code)
python run_mcp.py --http 8765  # streamable-http for remote / multi-client
```

## Register

Claude Desktop (`claude_desktop_config.json`) or a project `.mcp.json` for
Claude Code, with absolute paths:

```json
{
  "mcpServers": {
    "neon-screener": {
      "command": "/abs/path/.venv/bin/python",
      "args": ["/abs/path/run_mcp.py"]
    }
  }
}
```

Then ask in plain language, for example: "Screen US mega caps with RSI under 35,
add a dollar-volume column, and rank them by my Value factor," or "Read NVDA
across timeframes and chart it."

## Tools (16)

### Screening

- **`screen(market, filters, columns, match, sort, computed, stats, factor, limit, offset)`**
  The full engine. `filters` is a list of `{field, op, value}`; `value` may be a
  number, a list, or another field id (cross-field, so
  `{"field":"SMA50","op":"crosses_above","value":"SMA200"}` is a golden cross).
  `computed` adds derived columns from a sandboxed expression engine, `stats`
  adds `zscore`/`pctrank`/`rank`/`norm` across the result, `factor` is a weighted
  direction-aware composite score. Returns `{count, returned, market, ms,
  columns, rows, table}`.
- **`run_preset(preset_id, limit)`** Run one of the 47 named preset scans.
- **`run_factor_preset(factor_preset_id, market, filters, columns, limit)`** Rank
  a market by a named factor (Momentum, Value, Quality, Growth, Low-Vol).
- **`lookup_symbol(ticker, market, columns)`** One row by exact ticker.

### Discovery

- **`list_markets()`** The six markets (america, crypto, forex, futures, bond, cfd).
- **`search_fields(query, group, limit)`** Search the 1000+ field universe.
- **`list_operators()`** The filter operators and what value each expects.
- **`list_presets(group)`** The preset scans, optionally by group.
- **`list_factor_presets()`** The composite factor presets.
- **`server_stats()`** Server health: calls served, cache hit rate, errors.

### Symbol intelligence

- **`analyze(ticker, market)`** Read a symbol's chart into structured technical
  analysis: trend, momentum, range, rating, and plain-language signals. It is
  **multi-timeframe in one call**, RSI and MACD bias on the 1h, 4h, 1d, 1w, and
  1m at once with an alignment verdict, so nobody has to swap timeframes.
- **`technical_rating(ticker, market, timeframes)`** TradingView's own gauge
  (overall, moving averages, oscillators) as Strong Buy ... Strong Sell, across
  the timeframes you ask for.
- **`compare(tickers, columns, market)`** Several symbols side by side.
- **`search_symbols(query, market, limit)`** Resolve "apple" or "nvda" to rows.
- **`chart(ticker, market, interval, theme)`** A live TradingView chart deep link
  plus a ready-to-embed Advanced Chart widget config.
- **`sector_breakdown(market, filters, limit)`** Aggregate a screen by sector:
  count, average change, total market cap.

## Prompts (4)

Canned workflows the client can launch:

- **`momentum_breakouts(market)`** Find and read the strongest breakouts now.
- **`oversold_quality(market)`** Oversold names that are still high quality.
- **`rank_by_factor(factor, market)`** Rank a market by a factor and read the leaders.
- **`read_symbol(ticker)`** A full plain-language chart read for one symbol.

## Resources (3)

- **`screener://fields`** The full field catalog.
- **`screener://presets`** Every preset and factor preset.
- **`screener://operators`** The operator reference.

## Notes

- A short TTL cache sits in front of the engine to soften TradingView's
  rate-limit behavior under bursty agent use. `server_stats` reports the hit rate.
- The MCP server imports the backend modules directly, so it works without the
  web app running, and a screen behaves identically to the HTTP API (both call
  `backend.pipeline.run_screen`).
- Tests: `tests/test_mcp.py`. Offline tests cover wiring and the pure helpers;
  `@pytest.mark.live` tests exercise the real data tools.
