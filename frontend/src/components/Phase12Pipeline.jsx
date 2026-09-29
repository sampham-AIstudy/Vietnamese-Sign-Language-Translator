import React, { useState, useEffect, useRef, useCallback, useReducer } from 'react';
import CameraCapture from './CameraCapture';
import PredictionDisplay from './PredictionDisplay';
import { RefreshCw, Cpu, Circle, AlertTriangle } from 'lucide-react';
import { wsUrl, nowMs } from '../lib/ws';
import {
  initialLiveState, reduceLive, undoLastWord, discardReasonText, PIPELINE_HARMONIZED,
} from '../lib/liveProtocol';

const WS_PATH = '/ws/live-stream';

// Vietnamese text of the /ws/live-stream error codes (plan 04 §3.6); an unknown code is shown as sent.
const ERROR_TEXT = {
  message_too_large: 'Frame quá lớn (vượt giới hạn 1 MiB); phiên đã đóng.',
  model_unavailable: 'Mô hình Ký từ chưa sẵn sàng trên server; phiên đã đóng.',
  protocol_mismatch: 'Phiên bản giao thức của server khác bản giao diện hỗ trợ.',
  bad_message: 'Message gửi lên không hợp lệ.',
  bad_config: 'Cấu hình gửi lên không hợp lệ.',
  bad_timestamp: 'Timestamp của frame không hợp lệ.',
  decode_failed: 'Không giải mã được frame.',
  unsupported_format: 'Định dạng ảnh không được hỗ trợ (chỉ JPEG/PNG).',
  frame_too_large: 'Kích thước frame vượt giới hạn.',
  frame_too_small: 'Frame thấp hơn chiều cao mô hình yêu cầu.',
};

function errorText(code) {
  return ERROR_TEXT[code] ?? String(code ?? '');
}

function liveReducer(state, action) {
  switch (action.kind) {
    case 'message':
      return reduceLive(state, action.msg, action.now);
    case 'undo':
      return undoLastWord(state);
    case 'clearWords':
      return { ...state, words: [] };
    case 'reset':
      return initialLiveState();
    default:
      return state;
  }
}

/**
 * "Ký từ" mode: /ws/live-stream protocol_version 2 through the Vite proxy (same origin as the page).
 * The pure reducer (src/lib/liveProtocol.js) turns each server message into UI state:
 * - legacy (default model): prediction of every frame_result (sliding window);
 * - harmonized_v1: frame_result only reports the recording state; each sign_result / sign_discarded is shown as
 *   sent (no de-duplication, so a sign reported twice is visible and can be removed with "Xóa từ cuối").
 */
export default function Phase12Pipeline() {
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [connectError, setConnectError] = useState('');
  const [clientFps, setClientFps] = useState(null);
  const [live, dispatch] = useReducer(liveReducer, undefined, initialLiveState);
  const wsRef = useRef(null);
  const spokenRef = useRef(0);

  const getSocket = useCallback(() => wsRef.current, []);

  const speakText = (text) => {
    if (!text || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'vi-VN';
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('TTS error:', e);
    }
  };

  const connectWs = useCallback(() => {
    const cur = wsRef.current;
    if (cur && (cur.readyState === WebSocket.OPEN || cur.readyState === WebSocket.CONNECTING)) return;

    dispatch({ kind: 'reset' });
    spokenRef.current = 0;
    setConnectionStatus('connecting');
    setConnectError('');

    const url = wsUrl(window.location, WS_PATH);
    let ws;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      setConnectionStatus('error');
      setConnectError(`Lỗi khởi tạo WebSocket: ${err.message}`);
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      if (wsRef.current !== ws) return;
      setConnectionStatus('connected');
    };
    ws.onmessage = (event) => {
      if (wsRef.current !== ws) return;
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch (err) {
        dispatch({ kind: 'message', msg: null, now: nowMs() });
        return;
      }
      dispatch({ kind: 'message', msg, now: nowMs() });
    };
    ws.onerror = () => {
      if (wsRef.current !== ws) return;
      setConnectionStatus('error');
      setConnectError(`Không kết nối được ${WS_PATH} (qua proxy của trang). Hãy kiểm tra backend đã chạy.`);
    };
    ws.onclose = (event) => {
      if (wsRef.current !== ws) return;
      setConnectionStatus((prev) => (prev === 'error' ? prev : 'disconnected'));
      if (event.code === 1008) setConnectError('Server từ chối Origin của trang (1008).');
    };
  }, []);

  useEffect(() => {
    connectWs();
    return () => {
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws) ws.close();
    };
  }, [connectWs]);

  // speak each new word once
  useEffect(() => {
    if (live.words.length > spokenRef.current) speakText(live.words[live.words.length - 1]);
    spokenRef.current = live.words.length;
  }, [live.words]);

  const harmonized = live.pipeline === PIPELINE_HARMONIZED;
  const shown = harmonized
    ? { gloss: live.lastSign?.gloss ?? null, confidence: live.lastSign?.confidence ?? null, top5: live.lastSign?.top5 ?? [] }
    : { gloss: live.gloss, confidence: live.confidence, top5: live.top5 };
  const metrics = live.metrics || {};
  const recording = harmonized && live.status === 'RECORDING';
  const recordingPct = recording && live.maxSignS
    ? Math.min(100, Math.max(0, ((live.recordingS ?? 0) / live.maxSignS) * 100)) : 0;
  const errorShown = live.fatal ?? live.lastError?.code ?? null;

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 bg-slate-900 border border-slate-800 rounded-2xl">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand-500/20 text-brand-400 border border-brand-500/30">
              KÝ TỪ
            </span>
            <h1 className="text-base font-bold text-white">Nhận diện từ ký hiệu qua WebSocket</h1>
          </div>
          <div className="flex items-center gap-2 mt-2 flex-wrap text-xs">
            <span data-testid="live-pipeline"
                  className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono">
              <Circle className="w-2.5 h-2.5" />
              {live.pipeline ?? '—'}
            </span>
            <span data-testid="live-model" data-model-type={live.model?.model_type ?? ''}
                  data-is-default={live.model ? String(live.model.is_default) : ''}
                  className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono">
              <Cpu className="w-3 h-3" />
              {live.model ? `${live.model.model_type}${live.model.is_default ? ' (mặc định)' : ' (không mặc định)'}` : '—'}
            </span>
            {clientFps !== null && (
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400 font-mono">
                gửi {clientFps} FPS
              </span>
            )}
            {harmonized && live.lastSign && live.lastSign.client_e2e_ms !== null && (
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400 font-mono"
                    title="Từ frame kích hoạt kết quả tới lúc nhận sign_result (đồng hồ client)">
                e2e {Math.round(live.lastSign.client_e2e_ms)} ms
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {connectionStatus !== 'connected' && connectionStatus !== 'connecting' && (
            <button
              onClick={connectWs}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-brand-600 hover:bg-brand-500 text-white transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Thử Kết Nối Lại</span>
            </button>
          )}
        </div>
      </div>

      {/* Recording state (harmonized_v1 only) */}
      {recording && (
        <div data-testid="live-recording" className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-200">
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-semibold">Đang ghi ký hiệu</span>
            <span className="font-mono">
              {(live.recordingS ?? 0).toFixed(2)} s / {live.maxSignS ?? '—'} s
            </span>
          </div>
          <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full bg-rose-400 rounded-full" style={{ width: `${recordingPct}%` }} />
          </div>
        </div>
      )}

      {live.lastDiscard && (
        <div data-testid="live-discard" data-reason={live.lastDiscard.reason ?? ''}
             className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-200">
          Đoạn ký hiệu gần nhất bị bỏ: {discardReasonText(live.lastDiscard.reason)}
        </div>
      )}

      {errorShown && (
        <div data-testid="live-error" data-code={errorShown}
             className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-200 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>
            [{errorShown}] {errorText(errorShown)}
            {live.lastError?.detail && live.lastError.code === errorShown ? ` — ${live.lastError.detail}` : ''}
          </span>
        </div>
      )}

      {/* Main 2-Column Responsive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7">
          <CameraCapture
            getSocket={getSocket}
            isConnected={connectionStatus === 'connected' && !live.fatal}
            targetFps={25}
            drawSkeleton={true}
            landmarks={live.landmarks}
            onFpsUpdate={setClientFps}
            onError={(msg) => setConnectError(msg)}
          />
        </div>

        <div className="lg:col-span-5">
          <PredictionDisplay
            gloss={shown.gloss}
            confidence={shown.confidence}
            status={live.status}
            top5={shown.top5}
            fps={metrics.server_fps ?? null}
            latencyMs={metrics.server_total_ms ?? null}
            connectionStatus={connectionStatus}
            errorMessage={connectError}
            sentence={live.words}
            onClearSentence={() => dispatch({ kind: 'clearWords' })}
            onUndoWord={() => dispatch({ kind: 'undo' })}
            onSpeakSentence={speakText}
            bufferFill={harmonized ? null : live.bufferFill}
            bufferCapacity={harmonized ? null : live.bufferCapacity}
            resultLabel={harmonized ? 'Ký hiệu gần nhất (sign_result)' : 'Từ Nhận Diện (Top-1 Gloss)'}
          />
        </div>
      </div>
    </div>
  );
}
