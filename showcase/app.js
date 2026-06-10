// app.js - the Lightweight Charts demo on the showcase page.
//
// Loads TradingView's open-source Lightweight Charts (Apache 2.0, pulled from a
// CDN by index.html) and feeds it a synthetic series, so the panel renders with
// no data vendor. This is the "build your own" tier: the same library you would
// ship in your own product. No em dashes anywhere.

(function () {
  if (typeof LightweightCharts === 'undefined') return;
  const host = document.getElementById('lwc');
  if (!host) return;

  // ---- A deterministic random walk so the demo looks the same every load.
  function makeBars(n) {
    let seed = 1337;
    const rng = () => {
      seed = (seed * 1664525 + 1013904223) % 4294967296;
      return seed / 4294967296;
    };
    const bars = [];
    let price = 120;
    const start = new Date('2025-01-01T00:00:00Z');
    for (let i = 0; i < n; i++) {
      const drift = Math.sin(i / 14) * 1.4 + (rng() - 0.48) * 3.2;
      const open = price;
      const close = Math.max(5, open + drift);
      const high = Math.max(open, close) + rng() * 2.2;
      const low = Math.min(open, close) - rng() * 2.2;
      const d = new Date(start.getTime() + i * 86400000);
      bars.push({
        time: d.toISOString().slice(0, 10),
        open: +open.toFixed(2),
        high: +high.toFixed(2),
        low: +low.toFixed(2),
        close: +close.toFixed(2),
      });
      price = close;
    }
    return bars;
  }

  const bars = makeBars(140);
  const lineData = bars.map((b) => ({ time: b.time, value: b.close }));

  const chart = LightweightCharts.createChart(host, {
    autoSize: true,
    layout: {
      background: { type: 'solid', color: 'transparent' },
      textColor: '#8a8aa0',
      fontFamily: "'JetBrains Mono', monospace",
      attributionLogo: true,
    },
    grid: {
      vertLines: { color: 'rgba(255,255,255,0.05)' },
      horzLines: { color: 'rgba(255,255,255,0.05)' },
    },
    rightPriceScale: { borderColor: 'rgba(255,255,255,0.1)' },
    timeScale: { borderColor: 'rgba(255,255,255,0.1)' },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  });

  let series = null;

  function setSeries(kind) {
    if (series) { chart.removeSeries(series); series = null; }
    if (kind === 'line') {
      series = chart.addLineSeries({ color: '#00f0ff', lineWidth: 2 });
      series.setData(lineData);
    } else if (kind === 'area') {
      series = chart.addAreaSeries({
        lineColor: '#b026ff', topColor: 'rgba(176,38,255,0.4)', bottomColor: 'rgba(176,38,255,0)', lineWidth: 2,
      });
      series.setData(lineData);
    } else {
      series = chart.addCandlestickSeries({
        upColor: '#00ff88', downColor: '#ff003c',
        borderUpColor: '#00ff88', borderDownColor: '#ff003c',
        wickUpColor: '#00ff88', wickDownColor: '#ff003c',
      });
      series.setData(bars);
    }
    chart.timeScale().fitContent();
  }

  setSeries('candles');

  const controls = document.getElementById('lwc-controls');
  if (controls) {
    controls.addEventListener('click', (e) => {
      const btn = e.target.closest('.chip');
      if (!btn) return;
      controls.querySelectorAll('.chip').forEach((c) => c.classList.remove('on'));
      btn.classList.add('on');
      setSeries(btn.dataset.series);
    });
  }
})();
