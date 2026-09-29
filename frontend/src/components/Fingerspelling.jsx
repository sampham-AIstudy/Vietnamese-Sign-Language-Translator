import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Camera, CameraOff, Sparkles, Trash2, RotateCcw, Volume2, AlertTriangle, Circle, Square, Plus, Space,
} from 'lucide-react';
import { wsUrl, nowMs } from '../lib/ws';
import {
  buildSequenceBody, recordingStats, errorDetailText, SequenceBodyError,
  FS_TARGET_FPS, FS_JPEG_QUALITY, FS_MAX_IN_FLIGHT, FS_DEFAULT_TOP_K,
} from '../lib/fingerspelling';

const WS_PATH = '/ws/hand-landmarks';
const SEQUENCE_URL = '/api/fingerspelling/sequence';
const COMPOSE_URL = '/api/fingerspelling/compose';
const STATUS_URL = '/api/fingerspelling/status';
const DRAIN_TIMEOUT_MS = 2000;

const BODY_ERROR_TEXT = {
  empty: 'Chưa ghi được frame nào.',
  too_many_frames: 'Quá số frame tối đa của một ký hiệu.',
  frame_size_changed: 'Kích thước camera đổi giữa lượt ghi; hãy ghi lại.',
  bad_timestamps: 'Timestamp của frame không hợp lệ; hãy ghi lại.',
};

const WS_ERROR_TEXT = {
  message_too_large: 'Frame quá lớn (vượt giới hạn); phiên đã đóng.',
  model_unavailable: 'Bộ trích landmark bàn tay chưa sẵn sàng trên server; phiên đã đóng.',
  decode_failed: 'Server không giải mã được frame.',
  unsupported_format: 'Định dạng ảnh không được hỗ trợ.',
  frame_too_large: 'Kích thước frame vượt giới hạn.',
  bad_message: 'Message gửi lên không hợp lệ.',
  bad_timestamp: 'Timestamp không hợp lệ.',
  bad_config: 'Cấu hình không hợp lệ.',
};

function newRecording() {
  return { active: false, waitingReset: false, segmentId: null, frames: [], sent: 0, inFlight: 0, clientSkipped: 0 };
}

/**
 * "Đánh vần" (Level 1): webcam -> WS /ws/hand-landmarks (the server runs the training hand extractor on each
 * UNMIRRORED frame) -> hand_frame messages of one recorded sign -> POST /api/fingerspelling/sequence -> top-k.
 * Accepted tokens are composed by POST /api/fingerspelling/compose; the text shown is the server's `text` only.
 * The user starts and stops each sign (no automatic cut).
 */
export default function Fingerspelling() {
  const [status, setStatus] = useState({ loaded: false, available: false, message: 'Đang kiểm tra mô hình Cấp 1...' });
  const [wsStatus, setWsStatus] = useState('connecting');
  const [sessionInfo, setSessionInfo] = useState(null);
  const [cameraOn, setCameraOn] = useState(false);
  const [phase, setPhase] = useState('idle'); // idle | starting | recording | finishing
  const [liveCount, setLiveCount] = useState({ frames: 0, detected: 0, skipped: 0 });
  const [result, setResult] = useState(null); // {response, stats, responseMs}
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(0);
  const [tokens, setTokens] = useState([]);
  const [composed, setComposed] = useState({ text: '', warnings: [] });

  const wsRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const recRef = useRef(newRecording());
  const drainRef = useRef(null);
  const composeSeq = useRef(0);

  const maxFrames = sessionInfo?.limits?.max_frames_per_segment ?? null;

  // ---- model status
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await fetch(STATUS_URL);
        const data = await res.json();
        if (!alive) return;
        setStatus({
          loaded: true,
          available: Boolean(res.ok && data.available),
          message: data.message || (data.available ? 'Mô hình Cấp 1 đã sẵn sàng' : 'Chưa có mô hình Cấp 1'),
          numClasses: data.num_classes ?? null,
          modelType: data.model_type ?? null,
        });
      } catch (err) {
        if (alive) setStatus({ loaded: true, available: false, message: 'Không kết nối được backend (/api).' });
      }
    })();
    return () => { alive = false; };
  }, []);

  // ---- capture loop
  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const captureTick = useCallback(() => {
    const rec = recRef.current;
    const ws = wsRef.current;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!rec.active || !ws || ws.readyState !== WebSocket.OPEN || !video || !canvas) return;
    if (video.videoWidth === 0 || video.videoHeight === 0) return;
    if (maxFrames !== null && rec.sent >= maxFrames) return; // finishing is triggered by the frame count
    if (rec.inFlight >= FS_MAX_IN_FLIGHT) {
      rec.clientSkipped += 1;
      setLiveCount((c) => ({ ...c, skipped: rec.clientSkipped }));
      return;
    }
    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }
    canvas.getContext('2d', { willReadFrequently: true }).drawImage(video, 0, 0, canvas.width, canvas.height);
    const image = canvas.toDataURL('image/jpeg', FS_JPEG_QUALITY);
    rec.inFlight += 1;
    rec.sent += 1;
    ws.send(JSON.stringify({ image, timestamp: nowMs() }));
  }, [maxFrames]);

  const tickRef = useRef(captureTick);
  useEffect(() => { tickRef.current = captureTick; }, [captureTick]);

  // ---- finishing a recording: wait for the frames in flight, build the body, POST /sequence
  const finish = useCallback(async () => {
    const rec = recRef.current;
    if (!rec.active) return;
    rec.active = false;
    stopTimer();
    setPhase('finishing');
    const tStop = nowMs();
    await new Promise((resolve) => {
      const t0 = nowMs();
      const poll = () => {
        if (rec.inFlight <= 0 || nowMs() - t0 >= DRAIN_TIMEOUT_MS) resolve();
        else drainRef.current = setTimeout(poll, 20);
      };
      poll();
    });
    const segmentId = rec.segmentId;
    const frames = rec.frames.slice();
    const skipped = rec.clientSkipped + Math.max(0, rec.sent - frames.length);
    recRef.current = newRecording();
    let body;
    try {
      body = buildSequenceBody(frames, { segmentId, maxFrames: maxFrames ?? undefined, topK: FS_DEFAULT_TOP_K });
    } catch (e) {
      const code = e instanceof SequenceBodyError ? e.code : 'error';
      setError(BODY_ERROR_TEXT[code] ?? String(e.message || e));
      setPhase('idle');
      return;
    }
    const stats = recordingStats(body, skipped);
    try {
      const res = await fetch(SEQUENCE_URL, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => null);
      const responseMs = nowMs() - tStop;
      if (res.ok && data) {
        setResult({ response: data, stats, responseMs });
        setSelected(0);
      } else {
        setResult(null);
        setError(`[${res.status}] ${errorDetailText(data, res.status)}`);
      }
    } catch (err) {
      setResult(null);
      setError('Không gọi được /api/fingerspelling/sequence.');
    }
    setPhase('idle');
  }, [maxFrames]);

  const finishRef = useRef(finish);
  useEffect(() => { finishRef.current = finish; }, [finish]);

  const sessionInfoRef = useRef(null);
  useEffect(() => { sessionInfoRef.current = sessionInfo; }, [sessionInfo]);

  // ---- WebSocket /ws/hand-landmarks
  const connectWs = useCallback(() => {
    const cur = wsRef.current;
    if (cur && (cur.readyState === WebSocket.OPEN || cur.readyState === WebSocket.CONNECTING)) return;
    setWsStatus('connecting');
    const ws = new WebSocket(wsUrl(window.location, WS_PATH));
    wsRef.current = ws;
    ws.onopen = () => { if (wsRef.current === ws) setWsStatus('connected'); };
    ws.onclose = (ev) => {
      if (wsRef.current !== ws) return;
      setWsStatus('disconnected');
      if (ev.code === 1008) setError('Server từ chối Origin của trang (1008).');
      if (recRef.current.active) finishRef.current();
    };
    ws.onerror = () => { if (wsRef.current === ws) setWsStatus('error'); };
    ws.onmessage = (event) => {
      if (wsRef.current !== ws) return;
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      const rec = recRef.current;
      switch (msg.type) {
        case 'session_info':
          setSessionInfo(msg);
          break;
        case 'reset_done':
          if (rec.waitingReset) {
            rec.waitingReset = false;
            rec.segmentId = msg.segment_id;
            rec.active = true;
            setPhase('recording');
            stopTimer();
            timerRef.current = setInterval(() => tickRef.current(), Math.round(1000 / FS_TARGET_FPS));
          }
          break;
        case 'hand_frame':
          if (rec.segmentId !== null && msg.segment_id === rec.segmentId) {
            rec.inFlight = Math.max(0, rec.inFlight - 1);
            rec.frames.push(msg);
            setLiveCount((c) => ({
              frames: rec.frames.length,
              detected: c.detected + (msg.landmarks ? 1 : 0),
              skipped: rec.clientSkipped,
            }));
            const limit = sessionInfoRef.current?.limits?.max_frames_per_segment;
            if (rec.active && limit && rec.sent >= limit) finishRef.current();
          }
          break;
        case 'error':
          if (rec.inFlight > 0) rec.inFlight -= 1;
          setError(`[${msg.code}] ${WS_ERROR_TEXT[msg.code] ?? ''} ${msg.detail ?? ''}`.trim());
          break;
        default:
          break;
      }
    };
  }, []);

  useEffect(() => {
    connectWs();
    return () => {
      stopTimer();
      if (drainRef.current) clearTimeout(drainRef.current);
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws) ws.close();
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    };
  }, [connectWs]);

  // ---- camera
  const startCamera = async () => {
    if (streamRef.current) return true;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: FS_TARGET_FPS }, facingMode: 'user' },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraOn(true);
      return true;
    } catch (err) {
      console.error('Camera access error:', err);
      setError('Không thể truy cập camera. Vui lòng cấp quyền sử dụng camera trong trình duyệt.');
      return false;
    }
  };

  const stopCamera = () => {
    if (recRef.current.active) return;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraOn(false);
  };

  // ---- record / stop
  const startRecording = async () => {
    const ws = wsRef.current;
    if (!status.available || !ws || ws.readyState !== WebSocket.OPEN || phase !== 'idle') return;
    setError('');
    setResult(null);
    if (!(await startCamera())) return;
    recRef.current = { ...newRecording(), waitingReset: true };
    setLiveCount({ frames: 0, detected: 0, skipped: 0 });
    setPhase('starting');
    ws.send(JSON.stringify({ type: 'control', action: 'reset' }));
  };

  const stopRecording = () => {
    if (recRef.current.active) finish();
  };

  // ---- composer (text only from the server)
  useEffect(() => {
    const seq = ++composeSeq.current;
    if (tokens.length === 0) {
      setComposed({ text: '', warnings: [] });
      return;
    }
    (async () => {
      try {
        const res = await fetch(COMPOSE_URL, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tokens }),
        });
        const data = await res.json().catch(() => null);
        if (seq !== composeSeq.current) return;
        if (res.ok && data) setComposed({ text: data.text ?? '', warnings: data.warnings ?? [] });
        else setError(`[${res.status}] ${errorDetailText(data, res.status)}`);
      } catch {
        if (seq === composeSeq.current) setError('Không gọi được /api/fingerspelling/compose.');
      }
    })();
  }, [tokens]);

  const candidates = result?.response?.candidates ?? [];
  const chosen = candidates[selected] ?? null;

  const speakText = (text) => {
    if (!text || !window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'vi-VN';
    window.speechSynthesis.speak(utterance);
  };

  const canRecord = status.available && wsStatus === 'connected' && phase === 'idle';

  return (
    <div className="space-y-6">
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Đánh vần (Cấp 1): chữ cái và dấu thanh</h3>
            <p className="text-xs text-slate-400">
              Server trích 21 điểm bàn tay (MediaPipe Hands, cùng cấu hình lúc train) trên từng frame webcam; mô hình
              phân loại cả chuỗi frame của MỘT ký hiệu. Bấm Ghi, ký một chữ/dấu, rồi bấm Dừng.
            </p>
          </div>
        </div>

        {/* Model + connection status */}
        <div data-testid="fs-status" data-available={String(status.available)}
             className={`mb-4 p-4 rounded-xl border flex items-start gap-3 ${
               status.available ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                 : 'bg-amber-500/10 border-amber-500/30 text-amber-300'}`}>
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <div className="font-semibold">
              {status.available ? 'MÔ HÌNH CẤP 1 SẴN SÀNG' : 'MÔ HÌNH CẤP 1 CHƯA SẴN SÀNG — chức năng ghi bị khóa'}
            </div>
            <p className="leading-relaxed opacity-90">
              {status.message}
              {status.available && status.numClasses ? ` (${status.numClasses} lớp, ${status.modelType})` : ''}
            </p>
          </div>
        </div>
        <div className="mb-6 text-xs text-slate-400 flex items-center gap-2">
          <span data-testid="fs-ws" data-status={wsStatus}
                className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">
            {WS_PATH}: {wsStatus}
          </span>
          {wsStatus !== 'connected' && wsStatus !== 'connecting' && (
            <button onClick={connectWs} className="px-2 py-0.5 rounded bg-brand-600 text-white">Kết nối lại</button>
          )}
          {sessionInfo?.extractor && (
            <span className="font-mono">
              {sessionInfo.extractor.name} {sessionInfo.extractor.mediapipe_version}
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: camera + record controls */}
          <div className="lg:col-span-6 space-y-4">
            <div className="rounded-xl bg-slate-950 border border-slate-800 aspect-[4/3] flex items-center justify-center relative overflow-hidden">
              <canvas ref={canvasRef} className="hidden" />
              <video ref={videoRef} playsInline muted
                     className={`w-full h-full object-cover transform -scale-x-100 ${cameraOn ? 'block' : 'hidden'}`} />
              {!cameraOn && (
                <div className="text-center space-y-3 p-6">
                  <Camera className="w-8 h-8 text-brand-400 mx-auto" />
                  <p className="text-xs text-slate-400 max-w-xs">Camera bật khi bấm Ghi.</p>
                </div>
              )}
              {phase === 'recording' && (
                <div className="absolute top-3 left-3 flex items-center gap-2 bg-slate-950/80 px-2.5 py-1 rounded-full border border-slate-800 text-xs">
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                  <span className="text-white font-medium">ĐANG GHI</span>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button data-testid="fs-record" onClick={startRecording} disabled={!canRecord}
                      className="flex-1 py-2.5 px-4 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed text-white font-semibold text-xs flex items-center justify-center gap-2">
                <Circle className="w-3.5 h-3.5" /> Ghi
              </button>
              <button data-testid="fs-stop" onClick={stopRecording} disabled={phase !== 'recording'}
                      className="flex-1 py-2.5 px-4 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed text-white font-semibold text-xs flex items-center justify-center gap-2">
                <Square className="w-3.5 h-3.5" /> Dừng
              </button>
              <button onClick={stopCamera} disabled={!cameraOn || phase !== 'idle'}
                      className="py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 text-xs"
                      title="Tắt camera">
                <CameraOff className="w-4 h-4" />
              </button>
            </div>

            <div data-testid="fs-frames" data-frames={String(result ? result.stats.frames : liveCount.frames)}
                 className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 font-mono space-y-1">
              {result ? (
                <>
                  <div>Độ phân giải: {result.stats.resolution}</div>
                  <div>Số frame: {result.stats.frames} · có tay: {result.stats.detectedFrames} · bỏ qua phía client: {result.stats.clientSkipped}</div>
                  <div>FPS hiệu dụng: {result.stats.effectiveFps !== null ? result.stats.effectiveFps.toFixed(1) : '—'} · phản hồi sau Dừng: {Math.round(result.responseMs)} ms</div>
                </>
              ) : (
                <div>Lượt ghi: {liveCount.frames} frame · có tay: {liveCount.detected} · bỏ qua: {liveCount.skipped}
                  {maxFrames !== null ? ` · tối đa ${maxFrames}` : ''}</div>
              )}
            </div>

            {error && (
              <div data-testid="fs-error" className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs text-rose-200">
                {error}
              </div>
            )}
          </div>

          {/* Right: result + composer */}
          <div className="lg:col-span-6 space-y-4">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
              <span className="text-xs text-slate-400 uppercase font-semibold">Kết quả của ký hiệu vừa ghi</span>
              <div className="flex items-center justify-between">
                <div>
                  <div data-testid="fs-prediction" className="text-2xl font-extrabold text-white">
                    {result ? result.response.prediction : ''}
                  </div>
                  <span className="text-xs text-brand-400 font-mono">
                    Độ tin cậy của mô hình:{' '}
                    <span data-testid="fs-confidence" data-value={result ? String(result.response.confidence) : ''}>
                      {result ? `${(result.response.confidence * 100).toFixed(1)}%` : '—'}
                    </span>
                  </span>
                </div>
                <button data-testid="fs-add" onClick={() => chosen && setTokens((t) => [...t, chosen.class])}
                        disabled={!chosen}
                        className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium text-xs flex items-center gap-1">
                  <Plus className="w-3.5 h-3.5" /> Thêm {chosen ? `'${chosen.class}'` : ''}
                </button>
              </div>

              <div data-testid="fs-candidates" className="space-y-1.5 pt-2 border-t border-slate-900">
                {candidates.length === 0 ? (
                  <span className="text-[11px] text-slate-500">Chưa có kết quả.</span>
                ) : candidates.map((c, i) => (
                  <button key={i} onClick={() => setSelected(i)} data-class={c.class}
                          className={`w-full flex justify-between text-xs px-2 py-1 rounded ${
                            i === selected ? 'bg-brand-500/20 text-white' : 'text-slate-300 hover:bg-slate-900'}`}>
                    <span>{i + 1}. '{c.class}' {c.kind ? `(${c.kind === 'tone' ? 'dấu' : 'chữ'})` : ''}</span>
                    <span className="font-mono text-slate-400">{(c.confidence * 100).toFixed(1)}%</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400 uppercase font-semibold">Ghép chữ (server ghép)</span>
                <button onClick={() => speakText(composed.text)} disabled={!composed.text}
                        className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 disabled:opacity-40">
                  <Volume2 className="w-3.5 h-3.5" /> Đọc
                </button>
              </div>

              <div data-testid="fs-composed"
                   className="p-3 rounded-lg bg-slate-900 border border-slate-800 min-h-[50px] text-lg font-bold text-white tracking-wide">
                {composed.text}
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                token: {tokens.length ? tokens.map((t) => (t === ' ' ? '␣' : t)).join(' · ') : '(trống)'}
              </div>
              <div data-testid="fs-warnings" className="space-y-1">
                {composed.warnings.map((w, i) => (
                  <div key={i} className="text-[11px] text-amber-300">
                    [{w.code}] {w.message}
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap gap-2">
                <button data-testid="fs-space" onClick={() => setTokens((t) => [...t, ' '])}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 flex items-center gap-1">
                  <Space className="w-3 h-3" /> Dấu cách
                </button>
                <button data-testid="fs-backspace" onClick={() => setTokens((t) => t.slice(0, -1))}
                        disabled={tokens.length === 0}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-xs text-slate-200 flex items-center gap-1">
                  <RotateCcw className="w-3 h-3" /> Xóa lùi
                </button>
                <button data-testid="fs-clear" onClick={() => setTokens([])} disabled={tokens.length === 0}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-xs text-rose-400 flex items-center gap-1">
                  <Trash2 className="w-3 h-3" /> Xóa hết
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
