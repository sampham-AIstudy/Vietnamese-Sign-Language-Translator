/**
 * "Đánh vần" (Level 1) client helpers (plan 06 §3.2). Pure functions, no React / no I/O.
 *
 * The server extracts the hand landmarks (WS /ws/hand-landmarks, same MediaPipe settings as training) and returns
 * one `hand_frame` per webcam frame; the client collects the frames of ONE recorded sign and posts them to
 * POST /api/fingerspelling/sequence (contract of plan 03) with the body built by buildSequenceBody.
 */

// Design values, NOT measured (plan 06 §3.2): capture rate near the hauuto training clips (~23.6 fps), JPEG quality
// of the frames sent to /ws/hand-landmarks, frames allowed in flight before a capture is skipped.
export const FS_TARGET_FPS = 24;
export const FS_JPEG_QUALITY = 0.9;
export const FS_MAX_IN_FLIGHT = 2;
export const FS_DEFAULT_TOP_K = 5;

export class SequenceBodyError extends Error {
  constructor(code, message) {
    super(message || code);
    this.name = 'SequenceBodyError';
    this.code = code;
  }
}

/**
 * hand_frame messages -> body of POST /api/fingerspelling/sequence.
 * - only frames of `segmentId` (the current recording), ordered by frame_seq;
 * - landmarks[i] = the 21 x [x, y, z] returned by the server, or null without a hand (never an all-zero frame);
 * - handedness[i] = hand_frame.handedness ("" without a hand); timestamps_ms[i] = client_timestamp (must be numbers,
 *   non-decreasing);
 * - frame_width/frame_height of the frames; a size change inside the sign is an error (no guess);
 * - source_mirrored false (frames are never mirrored before extraction); top_k.
 * Errors (SequenceBodyError.code): empty, too_many_frames, frame_size_changed, bad_timestamps.
 */
export function buildSequenceBody(handFrames, { segmentId, maxFrames, topK = FS_DEFAULT_TOP_K } = {}) {
  const frames = (handFrames || [])
    .filter((m) => m && m.type === 'hand_frame' && m.segment_id === segmentId)
    .slice()
    .sort((a, b) => a.frame_seq - b.frame_seq);
  if (frames.length === 0) throw new SequenceBodyError('empty', 'no frame recorded');
  if (Number.isFinite(maxFrames) && frames.length > maxFrames) {
    throw new SequenceBodyError('too_many_frames', `${frames.length} frames > ${maxFrames}`);
  }
  const w = frames[0].frame_width;
  const h = frames[0].frame_height;
  if (frames.some((m) => m.frame_width !== w || m.frame_height !== h)) {
    throw new SequenceBodyError('frame_size_changed', 'camera frame size changed during the sign');
  }
  const timestamps = frames.map((m) => m.client_timestamp);
  if (timestamps.some((t) => typeof t !== 'number' || !Number.isFinite(t))
      || timestamps.some((t, i) => i > 0 && t < timestamps[i - 1])) {
    throw new SequenceBodyError('bad_timestamps', 'client timestamps must be numbers, non-decreasing');
  }
  return {
    landmarks: frames.map((m) => (Array.isArray(m.landmarks) && m.landmarks.length ? m.landmarks : null)),
    handedness: frames.map((m) => (typeof m.handedness === 'string' ? m.handedness : '')),
    timestamps_ms: timestamps,
    frame_width: w,
    frame_height: h,
    source_mirrored: false,
    top_k: topK,
  };
}

/** Summary shown next to a result: frames, frames with a hand, effective fps (from client timestamps). */
export function recordingStats(body, clientSkipped = 0) {
  const n = body.landmarks.length;
  const detected = body.landmarks.filter((f) => f !== null).length;
  const ts = body.timestamps_ms;
  const span = n >= 2 ? ts[n - 1] - ts[0] : 0;
  return {
    frames: n,
    detectedFrames: detected,
    clientSkipped,
    effectiveFps: span > 0 ? (n - 1) / (span / 1000) : null,
    resolution: `${body.frame_width}×${body.frame_height}`,
  };
}

/** FastAPI error body -> one line: {"detail": "..."} or {"detail": [{loc, msg, type}, ...]}. */
export function errorDetailText(body, status) {
  const d = body && body.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    return d.map((e) => `${Array.isArray(e.loc) ? e.loc.join('.') : ''}: ${e.msg ?? ''}`).join('; ');
  }
  return `HTTP ${status}`;
}
