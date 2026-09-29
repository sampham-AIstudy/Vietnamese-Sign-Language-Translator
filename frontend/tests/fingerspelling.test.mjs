// Plan 06 AC7-c: buildSequenceBody (hand_frame messages -> POST /api/fingerspelling/sequence body).
// The landmark arrays below are message-shape samples (not data): 21 points with distinct coordinates.
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildSequenceBody, recordingStats, errorDetailText, SequenceBodyError,
  FS_TARGET_FPS, FS_JPEG_QUALITY, FS_MAX_IN_FLIGHT,
} from '../src/lib/fingerspelling.js';

const HAND = Array.from({ length: 21 }, (_, i) => [0.3 + i / 100, 0.4 + i / 200, -i / 1000]);

function frame(seq, { seg = 1, hand = true, ts = 1000 + seq * 40, w = 640, h = 480 } = {}) {
  return {
    type: 'hand_frame', segment_id: seg, frame_seq: seq, received_seq: seq + 2, client_timestamp: ts,
    frame_width: w, frame_height: h, landmarks: hand ? HAND : null, handedness: hand ? 'Left' : '',
    handedness_score: hand ? 0.9 : null, metrics: { decode_ms: 1, extract_ms: 2, server_total_ms: 3 },
  };
}

function codeOf(fn) {
  try {
    fn();
  } catch (e) {
    assert.ok(e instanceof SequenceBodyError);
    return e.code;
  }
  return null;
}

test('design constants', () => {
  assert.equal(FS_TARGET_FPS, 24);
  assert.equal(FS_JPEG_QUALITY, 0.9);
  assert.equal(FS_MAX_IN_FLIGHT, 2);
});

test('frame without a hand -> null (never an all-zero frame)', () => {
  const body = buildSequenceBody([frame(0), frame(1, { hand: false }), frame(2)], { segmentId: 1, maxFrames: 300 });
  assert.equal(body.landmarks[1], null);
  assert.equal(body.handedness[1], '');
  for (const f of body.landmarks) {
    if (f !== null) assert.ok(f.flat().some((v) => v !== 0));
  }
  assert.deepEqual(body.landmarks[0], HAND);
  assert.equal(body.landmarks.length, body.handedness.length);
  assert.equal(body.landmarks.length, body.timestamps_ms.length);
});

test('ordered by frame_seq when the input is shuffled', () => {
  const body = buildSequenceBody([frame(2), frame(0), frame(3), frame(1)], { segmentId: 1, maxFrames: 300 });
  assert.deepEqual(body.timestamps_ms, [1000, 1040, 1080, 1120]);
});

test('frames of another segment_id are dropped', () => {
  const frames = [frame(0, { seg: 0 }), frame(1, { seg: 0 }), frame(0), frame(1), frame(2), frame(0, { seg: 2 })];
  const body = buildSequenceBody(frames, { segmentId: 1, maxFrames: 300 });
  assert.equal(body.landmarks.length, 3);
});

test('frame size change -> frame_size_changed', () => {
  assert.equal(codeOf(() => buildSequenceBody([frame(0), frame(1, { w: 1280, h: 720 })],
    { segmentId: 1, maxFrames: 300 })), 'frame_size_changed');
});

test('more than max_frames_per_segment -> too_many_frames', () => {
  const frames = Array.from({ length: 6 }, (_, i) => frame(i));
  assert.equal(codeOf(() => buildSequenceBody(frames, { segmentId: 1, maxFrames: 5 })), 'too_many_frames');
  assert.equal(buildSequenceBody(frames, { segmentId: 1, maxFrames: 6 }).landmarks.length, 6);
});

test('empty -> empty (also when only other segments are present)', () => {
  assert.equal(codeOf(() => buildSequenceBody([], { segmentId: 1, maxFrames: 300 })), 'empty');
  assert.equal(codeOf(() => buildSequenceBody([frame(0, { seg: 0 })], { segmentId: 1, maxFrames: 300 })), 'empty');
});

test('source_mirrored is false, top_k set, size copied', () => {
  const body = buildSequenceBody([frame(0)], { segmentId: 1, maxFrames: 300, topK: 3 });
  assert.equal(body.source_mirrored, false);
  assert.equal(body.top_k, 3);
  assert.equal(body.frame_width, 640);
  assert.equal(body.frame_height, 480);
  assert.equal(buildSequenceBody([frame(0)], { segmentId: 1, maxFrames: 300 }).top_k, 5);
});

test('timestamps_ms non-decreasing; decreasing or missing -> bad_timestamps', () => {
  const body = buildSequenceBody([frame(0, { ts: 5 }), frame(1, { ts: 5 }), frame(2, { ts: 9.5 })],
    { segmentId: 1, maxFrames: 300 });
  assert.deepEqual(body.timestamps_ms, [5, 5, 9.5]);
  for (let i = 1; i < body.timestamps_ms.length; i += 1) assert.ok(body.timestamps_ms[i] >= body.timestamps_ms[i - 1]);
  assert.equal(codeOf(() => buildSequenceBody([frame(0, { ts: 10 }), frame(1, { ts: 9 })],
    { segmentId: 1, maxFrames: 300 })), 'bad_timestamps');
  assert.equal(codeOf(() => buildSequenceBody([frame(0, { ts: null })], { segmentId: 1, maxFrames: 300 })),
    'bad_timestamps');
});

test('recordingStats and errorDetailText', () => {
  const body = buildSequenceBody([frame(0), frame(1, { hand: false }), frame(2)], { segmentId: 1, maxFrames: 300 });
  const st = recordingStats(body, 4);
  assert.equal(st.frames, 3);
  assert.equal(st.detectedFrames, 2);
  assert.equal(st.clientSkipped, 4);
  assert.equal(st.effectiveFps, 2 / 0.08);
  assert.equal(errorDetailText({ detail: 'x' }, 422), 'x');
  assert.equal(errorDetailText({ detail: [{ loc: ['body', 'landmarks'], msg: 'bad', type: 't' }] }, 422),
    'body.landmarks: bad');
  assert.equal(errorDetailText(null, 503), 'HTTP 503');
});
