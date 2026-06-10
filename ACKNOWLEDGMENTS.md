# Acknowledgments and thanks

NEON SCREENER stands on a lot of other people's work. Genuine thanks to all of
the below. Anything good here is built on these; anything broken is ours.

## TradingView

The data, the charts, and the inspiration. This project is a showcase of what
their platform makes possible, and it uses only TradingView data and libraries.

- TradingView: https://www.tradingview.com
- Free embeddable widgets (the showcase gallery): https://www.tradingview.com/widget/
- Lightweight Charts, the open-source charting core, Apache 2.0
  (the "build your own" panel in the showcase):
  https://github.com/tradingview/lightweight-charts
- Advanced Charts, the free access-gated charting library:
  https://www.tradingview.com/advanced-charts/

This project is independent and is not affiliated with or endorsed by TradingView.

## The library it is built on

- **`tradingview-screener`** by shner-elmo. The screener would not exist without
  it; it is the live, no-auth bridge to TradingView's scanner across every market.
  - PyPI: https://pypi.org/project/tradingview-screener/
  - Source: https://github.com/shner-elmo/TradingView-Screener

## MCP

- Model Context Protocol: https://modelcontextprotocol.io
- **`fastmcp`** by jlowin, the framework the MCP server is built on:
  https://github.com/jlowin/fastmcp

### TradingView MCP servers we studied

When designing the MCP layer we surveyed the existing TradingView MCP servers for
tool shapes and lessons (all MIT licensed). We borrowed concepts, not code, and
thank their authors:

- `ertugrul59/tradingview-chart-mcp` (chart images, the priority chart reference):
  https://github.com/ertugrul59/tradingview-chart-mcp
  (listing: https://www.pulsemcp.com/servers/ertugrul59-tradingview-chart)
- `fiale-plus/tradingview-mcp-server` (the cleanest screener tool design):
  https://github.com/fiale-plus/tradingview-mcp-server
- `atilaahmettaner/tradingview-mcp` (the resilience layer: throttle, cache, retry):
  https://github.com/atilaahmettaner/tradingview-mcp

## Backend stack

- FastAPI: https://fastapi.tiangolo.com
- Uvicorn: https://www.uvicorn.org
- pandas: https://pandas.pydata.org
- Requests: https://requests.readthedocs.io

## Type and fonts

- Chakra Petch: https://fonts.google.com/specimen/Chakra+Petch
- JetBrains Mono: https://www.jetbrains.com/lp/mono/
- Inter: https://rsms.me/inter/

All three are open-licensed (SIL Open Font License).

## Aesthetic

The synthwave / Bloomberg-terminal look is the house style of this project's
author. Lightweight Charts attribution (the small TradingView logo) is kept on by
default in the showcase, per its Apache 2.0 notice.
