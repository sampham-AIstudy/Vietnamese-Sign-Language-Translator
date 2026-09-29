// Plan 06 AC7-a: wsUrl goes through the page's origin (Vite proxy /ws), never a hard-coded backend port.
import test from 'node:test';
import assert from 'node:assert/strict';

import { wsUrl, nowMs } from '../src/lib/ws.js';

test('http page -> ws:// on the same host and port', () => {
  assert.equal(wsUrl({ protocol: 'http:', host: 'localhost:3000' }, '/ws/live-stream'),
    'ws://localhost:3000/ws/live-stream');
});

test('https page -> wss://', () => {
  assert.equal(wsUrl({ protocol: 'https:', host: 'example.org' }, '/ws/hand-landmarks'),
    'wss://example.org/ws/hand-landmarks');
});

test('port of the host is kept', () => {
  assert.equal(wsUrl({ protocol: 'http:', host: '127.0.0.1:3000' }, '/ws/hand-landmarks'),
    'ws://127.0.0.1:3000/ws/hand-landmarks');
  assert.equal(wsUrl({ protocol: 'https:', host: 'h:8443' }, 'ws/x'), 'wss://h:8443/ws/x');
});

test('nowMs is monotonic (performance clock)', () => {
  const a = nowMs();
  const b = nowMs();
  assert.equal(typeof a, 'number');
  assert.ok(Number.isFinite(a));
  assert.ok(b >= a);
});
