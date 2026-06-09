// openin.test.mjs - headless tests for the pure chartUrl builder.
// Run with: node --test frontend/js/openin.test.mjs
//
// chartUrl is window-free, so importing in bare Node is safe; the window-attach
// block in openin.js is guarded by a typeof check.

import { test } from 'node:test';
import assert from 'node:assert/strict';

const { chartUrl } = await import('./openin.js');

test('prefers the exchange-prefixed ticker', () => {
  assert.equal(
    chartUrl({ name: 'NVDA', ticker: 'NASDAQ:NVDA' }),
    'https://www.tradingview.com/chart/?symbol=NASDAQ%3ANVDA',
  );
});

test('falls back to bare name when no ticker', () => {
  assert.equal(
    chartUrl({ name: 'BTCUSD' }),
    'https://www.tradingview.com/chart/?symbol=BTCUSD',
  );
});

test('empty row yields empty string', () => {
  assert.equal(chartUrl({}), '');
  assert.equal(chartUrl(null), '');
});
