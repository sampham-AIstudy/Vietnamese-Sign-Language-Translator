// Plan 06 AC7-b: reduceLive over protocol-shaped sample messages (schema of plan 04 §3.6; protocol samples, not
// data). Every input state is deep-frozen: the reducer must never mutate it.
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  initialLiveState, reduceLive, undoLastWord, discardReasonText, PIPELINE_LEGACY, PIPELINE_HARMONIZED,
} from '../src/lib/liveProtocol.js';

function deepFreeze(o) {
  if (o && typeof o === 'object' && !Object.isFrozen(o)) {
    Object.freeze(o);
    for (const v of Object.values(o)) deepFreeze(v);
  }
  return o;
}

// reduce with a frozen state and a frozen message; also checks the input state is unchanged
function step(state, msg, now = 0) {
  const before = JSON.stringify(state);
  const next = reduceLive(deepFreeze(state), deepFreeze(msg), now);
  assert.equal(JSON.stringify(state), before);
  assert.notEqual(next, state);
  return next;
}

const SESSION_LEGACY = {
  type: 'session_info', protocol_version: 2, pipeline: 'legacy',
  model: { model_type: 'stgcn', checkpoint: 'stgcn_tier2_indomain.pt', checkpoint_sha256: null, is_default: true,
    num_classes: 487 },
  preprocessing: { target_len: 60 }, segmenter: null,
  limits: { max_message_bytes: 1048576, max_frame_side: 1920, min_frame_height: null },
};
const SESSION_HARMONIZED = {
  type: 'session_info', protocol_version: 2, pipeline: 'harmonized_v1',
  model: { model_type: 'stgcn_h360', checkpoint: 'stgcn_unified_best.pt', checkpoint_sha256: 'x', is_default: false,
    num_classes: 876 },
  preprocessing: { target_len: 64, process_height: 360 },
  segmenter: { max_sign_s: 4.0, rest_hold_s: 0.3 },
  limits: { max_message_bytes: 1048576, max_frame_side: 1920, min_frame_height: 360 },
};

function legacyFrame(status, gloss, extra = {}) {
  return {
    type: 'frame_result', pipeline: 'legacy', gloss, prediction: gloss, confidence: 0.5,
    top5: [{ gloss: gloss ?? 'x', confidence: 0.5 }], latency_ms: 1, fps: 20, status, sentence: [],
    is_confirmed: status === 'CONFIRMED', translated_text: null, oov_warning: false, is_signing: true,
    hand_detected: true, buffer_fill: 12, buffer_capacity: 60, landmarks: null,
    metrics: { client_timestamp: 1 }, ...extra,
  };
}

function harmonizedFrame(status, extra = {}) {
  return {
    type: 'frame_result', pipeline: 'harmonized_v1', frame_seq: 1, received_seq: 1, dropped_frames: 0,
    prediction: null, gloss: null, confidence: null, top5: [], status,
    segment: { state: status.toLowerCase(), segment_id: status === 'RECORDING' ? 3 : null, recording_s: 1.25,
      frames: 20, max_sign_s: 4.0 },
    is_signing: status === 'RECORDING', hand_detected: true, hand_active: true, landmarks: null,
    metrics: { client_timestamp: 5 }, ...extra,
  };
}

function signResult(gloss, trigger) {
  return {
    type: 'sign_result', segment_id: 3, frame_seq: 40, prediction: gloss, gloss, confidence: 0.7,
    top5: [{ gloss, confidence: 0.7 }, { gloss: 'khác', confidence: 0.1 }], end_reason: 'rest',
    segment: { duration_s: 1.2, frames: 30, dropped_frames: 0 },
    model: { model_type: 'stgcn_h360', is_default: false, pipeline: 'harmonized_v1' },
    metrics: { harmonize_ms: 1, infer_ms: 2, finalize_ms: 3, trigger_client_timestamp: trigger, rest_hold_s: 0.3 },
  };
}

test('session_info v2 legacy', () => {
  const s = step(initialLiveState(), SESSION_LEGACY);
  assert.equal(s.pipeline, PIPELINE_LEGACY);
  assert.equal(s.protocolVersion, 2);
  assert.deepEqual(s.model, { model_type: 'stgcn', is_default: true });
  assert.equal(s.maxSignS, null);
  assert.equal(s.limits.max_message_bytes, 1048576);
  assert.equal(s.fatal, null);
});

test('session_info v2 harmonized', () => {
  const s = step(initialLiveState(), SESSION_HARMONIZED);
  assert.equal(s.pipeline, PIPELINE_HARMONIZED);
  assert.deepEqual(s.model, { model_type: 'stgcn_h360', is_default: false });
  assert.equal(s.maxSignS, 4.0);
  assert.equal(s.limits.min_frame_height, 360);
  assert.equal(s.fatal, null);
});

test('protocol_version 3 -> fatal protocol_mismatch', () => {
  const s = step(initialLiveState(), { ...SESSION_LEGACY, protocol_version: 3 });
  assert.equal(s.fatal, 'protocol_mismatch');
});

test('legacy CONFIRMED transition adds one word; repeated CONFIRMED of the same gloss does not', () => {
  let s = step(initialLiveState(), SESSION_LEGACY);
  s = step(s, legacyFrame('DETECTING', 'xin chào'));
  assert.deepEqual(s.words, []);
  s = step(s, legacyFrame('CONFIRMED', 'xin chào'));
  assert.deepEqual(s.words, ['xin chào']);
  s = step(s, legacyFrame('CONFIRMED', 'xin chào'));
  assert.deepEqual(s.words, ['xin chào']);
  s = step(s, legacyFrame('CONFIRMED', 'cảm ơn'));
  assert.deepEqual(s.words, ['xin chào', 'cảm ơn']);
  assert.equal(s.status, 'CONFIRMED');
  assert.equal(s.gloss, 'cảm ơn');
  assert.equal(s.confidence, 0.5);
  assert.equal(s.frameResults, 4);
});

test('legacy buffer_capacity comes from the message (no hard-coded 60)', () => {
  let s = step(initialLiveState(), SESSION_LEGACY);
  s = step(s, legacyFrame('IDLE', null, { buffer_fill: 7, buffer_capacity: 45 }));
  assert.equal(s.bufferCapacity, 45);
  assert.equal(s.bufferFill, 7);
  assert.deepEqual(s.words, []);
});

test('harmonized frame_result never changes lastSign nor the displayed prediction', () => {
  let s = step(initialLiveState(), SESSION_HARMONIZED);
  s = step(s, signResult('xin chào', 100), 150);
  const sign = s.lastSign;
  s = step(s, harmonizedFrame('RECORDING'));
  assert.equal(s.lastSign, sign);
  assert.equal(s.status, 'RECORDING');
  assert.equal(s.recordingS, 1.25);
  assert.equal(s.maxSignS, 4.0);
  assert.equal(s.handActive, true);
  assert.equal(s.gloss, null);
  assert.deepEqual(s.top5, []);
  s = step(s, harmonizedFrame('WAIT_REST'));
  assert.equal(s.lastSign, sign);
  assert.deepEqual(s.words, ['xin chào']);
});

test('two sign_result with the same gloss -> both in words (no de-duplication)', () => {
  let s = step(initialLiveState(), SESSION_HARMONIZED);
  s = step(s, signResult('xin chào', 100), 150);
  s = step(s, signResult('xin chào', 200), 260);
  assert.deepEqual(s.words, ['xin chào', 'xin chào']);
  assert.equal(s.lastSign.gloss, 'xin chào');
  assert.equal(s.lastSign.top5.length, 2);
  assert.equal(s.lastSign.segment_id, 3);
});

test('client_e2e_ms = nowMs - trigger_client_timestamp (null when no trigger)', () => {
  let s = step(initialLiveState(), SESSION_HARMONIZED);
  s = step(s, signResult('a', 1000.5), 1234.25);
  assert.equal(s.lastSign.client_e2e_ms, 1234.25 - 1000.5);
  s = step(s, signResult('a', null), 99);
  assert.equal(s.lastSign.client_e2e_ms, null);
});

test('sign_discarded stores the reason', () => {
  let s = step(initialLiveState(), SESSION_HARMONIZED);
  s = step(s, { type: 'sign_discarded', segment_id: 4, frame_seq: 9, reason: 'too_short',
    segment: { duration_s: 0.1, frames: 3 } });
  assert.equal(s.lastDiscard.reason, 'too_short');
  assert.deepEqual(s.lastDiscard.segment, { duration_s: 0.1, frames: 3 });
  assert.equal(discardReasonText('too_short'), 'ký hiệu quá ngắn');
  assert.equal(discardReasonText('something_new'), 'something_new');
});

test('error message_too_large / model_unavailable -> fatal; other codes are not fatal', () => {
  let s = step(initialLiveState(), SESSION_LEGACY);
  s = step(s, { type: 'error', code: 'decode_failed', detail: 'image is not valid base64', received_seq: 3 });
  assert.deepEqual(s.lastError, { code: 'decode_failed', detail: 'image is not valid base64' });
  assert.equal(s.fatal, null);
  s = step(s, { type: 'error', code: 'message_too_large', detail: 'too big', received_seq: 4 });
  assert.equal(s.fatal, 'message_too_large');
  const u = step(initialLiveState(), { type: 'error', code: 'model_unavailable', detail: 'x', received_seq: null });
  assert.equal(u.fatal, 'model_unavailable');
});

test('unknown message type -> unknownMessages + 1, no throw', () => {
  let s = step(initialLiveState(), { type: 'brand_new_type' });
  s = step(s, { type: 'another' });
  assert.equal(s.unknownMessages, 2);
});

test('undoLastWord removes the last word only', () => {
  let s = step(initialLiveState(), SESSION_HARMONIZED);
  s = step(s, signResult('a', 1), 2);
  s = step(s, signResult('b', 1), 2);
  const u = undoLastWord(deepFreeze(s));
  assert.deepEqual(u.words, ['a']);
  assert.deepEqual(s.words, ['a', 'b']);
});
