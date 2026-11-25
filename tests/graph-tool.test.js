import test from 'node:test';
import assert from 'node:assert/strict';
import { createGraphSvg } from '../graph-tool.js';

test('plots a polynomial and returns a responsive SVG path', () => {
  const svg = createGraphSvg('y=x^2');
  assert.match(svg, /<svg class="ultron-graph"/);
  assert.match(svg, /class="graph-curve"/);
  assert.match(svg, /aria-label="Graph of y=x\^2"/);
  assert.match(svg, /M[0-9.]+ [0-9.]+/);
});

test('supports trig functions and constants', () => {
  assert.match(createGraphSvg('sin(x)+cos(x)'), /class="graph-curve"/);
  assert.match(createGraphSvg('sqrt(abs(x))+pi'), /class="graph-curve"/);
});

test('rejects invalid syntax, unknown identifiers, and injected markup', () => {
  assert.throws(() => createGraphSvg('x;alert(1)'), /Unsupported graph character/);
  assert.throws(() => createGraphSvg('unknown(x)'), /Unknown graph name/);
  assert.throws(() => createGraphSvg('x + <script>'), /Unsupported graph character/);
});

test('rejects invalid domains and resource settings', () => {
  assert.throws(() => createGraphSvg('x', {minX: 2, maxX: 2}), /valid x-domain/);
  assert.throws(() => createGraphSvg('x', {samples: 50000}), /sampling/);
});
