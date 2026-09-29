/**
 * Pure reducer of the /ws/live-stream protocol_version 2 messages ("Ký từ" mode; plan 04 §3.6, plan 06 §3.4).
 * No React, no I/O: `reduceLive(state, msg, nowMs)` returns a NEW state and never mutates its inputs.
 *
 * - session_info: pipeline ("legacy" | "harmonized_v1"), model, segmenter.max_sign_s, limits;
 *   protocol_version !== 2 -> fatal "protocol_mismatch".
 * - frame_result (legacy): prediction fields of the sliding window (gloss/confidence/top5/status/buffer_*);
 *   a CONFIRMED gloss different from the last word is appended to `words` (behaviour of the former UI).
 * - frame_result (harmonized_v1): recording state only (never a prediction; lastSign is left untouched).
 * - sign_result: lastSign + its gloss appended to `words` (NO de-duplication: every sign the server reports is
 *   shown); client_e2e_ms = nowMs - metrics.trigger_client_timestamp when that is a number.
 * - sign_discarded: lastDiscard {reason, segment}.
 * - error: lastError {code, detail}; message_too_large / model_unavailable -> fatal (the server closes).
 * - any other type: unknownMessages + 1.
 */

export const LIVE_PROTOCOL_VERSION = 2;
export const PIPELINE_LEGACY = 'legacy';
export const PIPELINE_HARMONIZED = 'harmonized_v1';
const FATAL_ERRORS = new Set(['message_too_large', 'model_unavailable']);

export function initialLiveState() {
  return {
    pipeline: null,
    protocolVersion: null,
    model: null,
    maxSignS: null,
    limits: null,
    fatal: null,
    // legacy prediction (frame_result)
    gloss: null,
    confidence: null,
    top5: [],
    bufferFill: 0,
    bufferCapacity: null,
    // both pipelines
    status: 'IDLE',
    landmarks: null,
    metrics: null,
    frameResults: 0,
    // harmonized recording state (frame_result)
    recordingS: null,
    handDetected: false,
    handActive: false,
    // events
    words: [],
    lastSign: null,
    lastDiscard: null,
    lastError: null,
    unknownMessages: 0,
  };
}

function isNumber(v) {
  return typeof v === 'number' && Number.isFinite(v);
}

function sessionInfo(state, msg) {
  const next = {
    ...state,
    pipeline: msg.pipeline ?? null,
    protocolVersion: msg.protocol_version ?? null,
    model: msg.model ? { model_type: msg.model.model_type ?? null, is_default: msg.model.is_default ?? null } : null,
    maxSignS: msg.segmenter && isNumber(msg.segmenter.max_sign_s) ? msg.segmenter.max_sign_s : null,
    limits: msg.limits ? { ...msg.limits } : null,
  };
  if (msg.protocol_version !== LIVE_PROTOCOL_VERSION) next.fatal = 'protocol_mismatch';
  return next;
}

function legacyFrame(state, msg) {
  const next = {
    ...state,
    gloss: msg.gloss ?? null,
    confidence: isNumber(msg.confidence) ? msg.confidence : null,
    top5: Array.isArray(msg.top5) ? msg.top5 : [],
    status: msg.status ?? state.status,
    bufferFill: isNumber(msg.buffer_fill) ? msg.buffer_fill : state.bufferFill,
    bufferCapacity: isNumber(msg.buffer_capacity) ? msg.buffer_capacity : state.bufferCapacity,
    handDetected: Boolean(msg.hand_detected),
    landmarks: msg.landmarks ?? null,
    metrics: msg.metrics ?? null,
    frameResults: state.frameResults + 1,
  };
  const g = msg.gloss;
  if (msg.status === 'CONFIRMED' && g && g !== '...' && state.words[state.words.length - 1] !== g) {
    next.words = [...state.words, g];
  }
  return next;
}

function harmonizedFrame(state, msg) {
  const seg = msg.segment || {};
  return {
    ...state,
    status: msg.status ?? state.status,
    recordingS: isNumber(seg.recording_s) ? seg.recording_s : null,
    maxSignS: isNumber(seg.max_sign_s) ? seg.max_sign_s : state.maxSignS,
    handDetected: Boolean(msg.hand_detected),
    handActive: Boolean(msg.hand_active),
    landmarks: msg.landmarks ?? null,
    metrics: msg.metrics ?? null,
    frameResults: state.frameResults + 1,
  };
}

function signResult(state, msg, nowMs) {
  const trigger = msg.metrics ? msg.metrics.trigger_client_timestamp : null;
  const lastSign = {
    gloss: msg.gloss ?? null,
    confidence: isNumber(msg.confidence) ? msg.confidence : null,
    top5: Array.isArray(msg.top5) ? msg.top5 : [],
    segment: msg.segment ?? null,
    segment_id: msg.segment_id ?? null,
    client_e2e_ms: isNumber(trigger) && isNumber(nowMs) ? nowMs - trigger : null,
  };
  return {
    ...state,
    lastSign,
    words: msg.gloss ? [...state.words, msg.gloss] : state.words,
  };
}

export function reduceLive(state, msg, nowMs) {
  if (!msg || typeof msg !== 'object') {
    return { ...state, unknownMessages: state.unknownMessages + 1 };
  }
  switch (msg.type) {
    case 'session_info':
      return sessionInfo(state, msg);
    case 'frame_result':
      return (msg.pipeline ?? state.pipeline) === PIPELINE_HARMONIZED ? harmonizedFrame(state, msg) : legacyFrame(state, msg);
    case 'sign_result':
      return signResult(state, msg, nowMs);
    case 'sign_discarded':
      return { ...state, lastDiscard: { reason: msg.reason ?? null, segment: msg.segment ?? null } };
    case 'error': {
      const next = { ...state, lastError: { code: msg.code ?? null, detail: msg.detail ?? null } };
      if (FATAL_ERRORS.has(msg.code)) next.fatal = msg.code;
      return next;
    }
    default:
      return { ...state, unknownMessages: state.unknownMessages + 1 };
  }
}

/** Removes the last word (the "Xóa từ cuối" button). */
export function undoLastWord(state) {
  return state.words.length ? { ...state, words: state.words.slice(0, -1) } : state;
}

/** Vietnamese text of a sign_discarded reason (src/inference/sign_segmenter.py, src/inference/harmonized_live.py);
 * an unknown reason is shown as sent. */
export const DISCARD_REASON_VI = {
  too_short: 'ký hiệu quá ngắn',
  too_long: 'ký hiệu quá dài',
  stream_gap: 'luồng khung bị ngắt quãng',
  frame_size_changed: 'kích thước camera đổi giữa ký hiệu',
  reset: 'đã đặt lại giữa ký hiệu',
  no_hand_frames: 'không thấy tay trong đoạn',
};

export function discardReasonText(reason) {
  return DISCARD_REASON_VI[reason] ?? String(reason ?? '');
}
