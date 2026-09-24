import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Activity,
  AlertCircle,
  Camera,
  Check,
  Clock,
  Copy,
  Cpu,
  Gauge,
  Play,
  RotateCcw,
  Settings2,
  Sliders,
  Square,
  Trash2,
  Volume2,
  Wifi,
  Zap,
  Sparkles,
} from 'lucide-react';

export default function RealtimeStream({ onSaveHistory }) {
  // Streaming state
  const [isStreaming, setIsStreaming] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected'); // 'disconnected' | 'connecting' | 'connected' | 'error'
  const [errorMessage, setErrorMessage] = useState('');

  // AI Recognition Output
  const [prediction, setPrediction] = useState('...');
  const [confidence, setConfidence] = useState(0.0);
  const [isSigning, setIsSigning] = useState(false);
  const [top5Candidates, setTop5Candidates] = useState([]);
  const [accumulatedSentence, setAccumulatedSentence] = useState([]);
  const [translatedText, setTranslatedText] = useState('');
  const [oovWarning, setOovWarning] = useState(null);

  // Telemetry & Latency Metrics
  const [telemetry, setTelemetry] = useState({
    e2eLatency: 0,
    serverPreprocess: 0,
    serverInfer: 0,
    serverTotal: 0,
    clientFps: 0,
    serverFps: 0,
    bufferFrames: 0,
    networkLatency: 0,
  });
  const [latencyHistory, setLatencyHistory] = useState([]);

  // Settings & Configuration
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.65);
  const [debounceSec, setDebounceSec] = useState(1.2);
  const [windowSec, setWindowSec] = useState(2.0);
  const [drawSkeleton, setDrawSkeleton] = useState(true);
  const [targetFps, setTargetFps] = useState(24);

  // References
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const wsRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const frameCountRef = useRef(0);
  const fpsTimerRef = useRef(Date.now());
  const copyToastTimerRef = useRef(null);
  const [copied, setCopied] = useState(false);

  // 1. Text to speech
  const speakText = (text) => {
    if (!text || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'vi-VN';
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  };

  // 2. Draw MediaPipe skeleton keypoints onto HTML5 overlay canvas
  const drawLandmarks = useCallback(
    (landmarks) => {
      const canvas = overlayCanvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (!drawSkeleton || !landmarks) return;

      const { pose = [], left_hand = [], right_hand = [] } = landmarks;
      const w = canvas.width;
      const h = canvas.height;

      // Draw Upper Body Pose
      if (pose.length > 0) {
        ctx.fillStyle = '#38bdf8'; // Sky blue
        pose.forEach(([x, y]) => {
          if (x > 0 && y > 0) {
            ctx.beginPath();
            ctx.arc(x * w, y * h, 4, 0, 2 * Math.PI);
            ctx.fill();
          }
        });
      }

      // Draw Left Hand (Green)
      if (left_hand.length > 0) {
        ctx.fillStyle = '#22c55e'; // Emerald green
        ctx.strokeStyle = '#16a34a';
        ctx.lineWidth = 2;
        left_hand.forEach(([x, y]) => {
          if (x > 0 && y > 0) {
            ctx.beginPath();
            ctx.arc(x * w, y * h, 4, 0, 2 * Math.PI);
            ctx.fill();
          }
        });
      }

      // Draw Right Hand (Purple/Cyan)
      if (right_hand.length > 0) {
        ctx.fillStyle = '#a855f7'; // Purple
        ctx.strokeStyle = '#9333ea';
        ctx.lineWidth = 2;
        right_hand.forEach(([x, y]) => {
          if (x > 0 && y > 0) {
            ctx.beginPath();
            ctx.arc(x * w, y * h, 4, 0, 2 * Math.PI);
            ctx.fill();
          }
        });
      }
    },
    [drawSkeleton]
  );

  // 3. Connect WebSocket to Python AI Backend
  const connectWebSocket = useCallback(() => {
    setConnectionStatus('connecting');
    setErrorMessage('');

    // Determine WS URL (default port 8000 for Python AI service)
    const wsUrl = `ws://${window.location.hostname}:8000/ws/live-stream`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'frame_result') {
          const now = Date.now();
          const rtt = data.metrics.client_timestamp ? now - data.metrics.client_timestamp : 0;
          const networkLat = Math.max(0, rtt - data.metrics.server_total_ms);

          setPrediction(data.prediction);
          setConfidence(data.confidence);
          setIsSigning(data.is_signing);
          setTop5Candidates(data.top5 || []);

          if (data.should_append && data.prediction && data.prediction !== '...') {
            setAccumulatedSentence((prev) => [...prev, data.prediction]);
            speakText(data.prediction);
          }

          if (data.translated_text) {
            setTranslatedText(data.translated_text);
          }
          if (data.oov_warning !== undefined) {
            setOovWarning(data.oov_warning);
          }

          // Update Telemetry metrics
          const newTelemetry = {
            e2eLatency: rtt,
            serverPreprocess: data.metrics.server_preprocess_ms,
            serverInfer: data.metrics.server_infer_ms,
            serverTotal: data.metrics.server_total_ms,
            clientFps: telemetry.clientFps,
            serverFps: data.metrics.server_fps,
            bufferFrames: data.metrics.buffer_frames,
            networkLatency: Math.round(networkLat),
          };
          setTelemetry(newTelemetry);

          // Update latency history sparkline (last 30 samples)
          setLatencyHistory((prev) => [...prev.slice(-29), rtt]);

          // Draw skeletal keypoints
          drawLandmarks(data.landmarks);
        }
      } catch (err) {
        console.error('Failed parsing WS message:', err);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket Error:', err);
      setConnectionStatus('error');
      setErrorMessage('Không thể kết nối đến Python AI Backend (:8000/ws/live-stream). Vui lòng đảm bảo FastAPI backend đang chạy.');
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
    };
  }, [drawLandmarks, telemetry.clientFps]);

  // 4. Start Camera Stream & Capture Loop
  const startStreaming = async () => {
    try {
      setErrorMessage('');
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { ideal: targetFps },
          facingMode: 'user',
        },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      connectWebSocket();
      setIsStreaming(true);

      // Start frame capture loop
      const frameInterval = 1000 / targetFps;
      intervalRef.current = setInterval(() => {
        captureAndSendFrame();
      }, frameInterval);
    } catch (err) {
      console.error('Error accessing camera:', err);
      setErrorMessage('Không thể truy cập camera. Vui lòng cấp quyền sử dụng camera trong trình duyệt.');
    }
  };

  // 5. Capture canvas snapshot and send over WebSocket
  const captureAndSendFrame = () => {
    if (!videoRef.current || !canvasRef.current || !wsRef.current) return;
    if (wsRef.current.readyState !== WebSocket.OPEN) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video.videoWidth === 0 || video.videoHeight === 0) return;

    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      if (overlayCanvasRef.current) {
        overlayCanvasRef.current.width = video.videoWidth;
        overlayCanvasRef.current.height = video.videoHeight;
      }
    }

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Calculate Client FPS
    frameCountRef.current += 1;
    const now = Date.now();
    const elapsed = now - fpsTimerRef.current;
    if (elapsed >= 1000) {
      const calculatedFps = Math.round((frameCountRef.current * 1000) / elapsed);
      setTelemetry((prev) => ({ ...prev, clientFps: calculatedFps }));
      frameCountRef.current = 0;
      fpsTimerRef.current = now;
    }

    // Backpressure guard: skip frame if socket buffer has backlog
    if (wsRef.current.bufferedAmount && wsRef.current.bufferedAmount > 65536) {
      return;
    }

    // Convert to JPEG base64 (quality 0.75 for fast network transmission)
    const base64Image = canvas.toDataURL('image/jpeg', 0.75);

    const payload = {
      image: base64Image,
      timestamp: Date.now(),
      config: {
        confidence_threshold: confidenceThreshold,
        debounce_sec: debounceSec,
        window_sec: windowSec,
      },
    };

    wsRef.current.send(JSON.stringify(payload));
  };

  // 6. Stop Streaming
  const stopStreaming = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    const overlayCanvas = overlayCanvasRef.current;
    if (overlayCanvas) {
      const ctx = overlayCanvas.getContext('2d');
      ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    }

    setIsStreaming(false);
    setConnectionStatus('disconnected');
    setPrediction('...');
    setConfidence(0.0);
    setIsSigning(false);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopStreaming();
    };
  }, []);

  const handleCopySentence = () => {
    const text = accumulatedSentence.join(' ');
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    if (copyToastTimerRef.current) clearTimeout(copyToastTimerRef.current);
    copyToastTimerRef.current = setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveToHistory = () => {
    const text = accumulatedSentence.join(' ');
    if (!text) return;
    if (onSaveHistory) {
      onSaveHistory(text, confidence, accumulatedSentence);
    }
  };

  // Latency quality color
  const getLatencyColor = (ms) => {
    if (ms <= 35) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    if (ms <= 70) return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
  };

  return (
    <div className="space-y-6">
      {/* Top Banner Alert if any error */}
      {errorMessage && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <p className="text-sm font-medium">{errorMessage}</p>
        </div>
      )}

      {/* Main Grid: Video Stream & Telemetry / Predictions */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: Live Camera Feed & Canvas HUD (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="relative rounded-2xl overflow-hidden bg-slate-900 border border-slate-800 shadow-2xl aspect-[4/3] flex items-center justify-center">
            {/* HTML5 Video Element */}
            <video
              ref={videoRef}
              playsInline
              muted
              className="w-full h-full object-cover"
              style={{ display: isStreaming ? 'block' : 'none' }}
            />

            {/* Hidden capture canvas */}
            <canvas ref={canvasRef} className="hidden" />

            {/* Skeletal Landmarks Overlay Canvas */}
            <canvas
              ref={overlayCanvasRef}
              className="absolute inset-0 w-full h-full pointer-events-none z-10"
            />

            {/* Video Placeholder when not streaming */}
            {!isStreaming && (
              <div className="text-center p-8 space-y-4">
                <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto text-slate-400 border border-slate-700 shadow-inner">
                  <Camera className="w-8 h-8 text-brand-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Camera Sẵn Sàng</h3>
                  <p className="text-sm text-slate-400 max-w-sm mt-1">
                    Bấm nút <strong>"Bắt Đầu Nhận Diện"</strong> bên dưới để truyền luồng video thời gian thực đến mô hình AI.
                  </p>
                </div>
              </div>
            )}

            {/* Live Video HUD Banner */}
            {isStreaming && (
              <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none z-20">
                <div className="flex items-center gap-2 bg-slate-950/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-800 text-xs text-white shadow-lg">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
                  <span className="font-semibold text-emerald-400">REC LIVE</span>
                  <span className="text-slate-500">|</span>
                  <span>{telemetry.clientFps} FPS</span>
                </div>

                <div className="flex items-center gap-2 bg-slate-950/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-800 text-xs shadow-lg">
                  <span className="text-slate-400">E2E Latency:</span>
                  <span className={`font-mono font-bold px-1.5 py-0.5 rounded border text-xs ${getLatencyColor(telemetry.e2eLatency)}`}>
                    {telemetry.e2eLatency} ms
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Camera Controls & Quick Switches */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
            <div className="flex items-center gap-3">
              {!isStreaming ? (
                <button
                  onClick={startStreaming}
                  className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-brand-600 to-emerald-500 hover:from-brand-500 hover:to-emerald-400 text-white font-semibold rounded-xl shadow-lg shadow-brand-500/25 transition-all transform active:scale-95"
                >
                  <Play className="w-4 h-4 fill-white" />
                  Bắt Đầu Nhận Diện
                </button>
              ) : (
                <button
                  onClick={stopStreaming}
                  className="flex items-center gap-2 px-5 py-2.5 bg-rose-600 hover:bg-rose-500 text-white font-semibold rounded-xl shadow-lg shadow-rose-500/25 transition-all transform active:scale-95"
                >
                  <Square className="w-4 h-4 fill-white" />
                  Dừng Truyền Luồng
                </button>
              )}

              <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={drawSkeleton}
                  onChange={(e) => setDrawSkeleton(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-700 text-brand-500 focus:ring-brand-500 bg-slate-800"
                />
                Hiện khung xương MediaPipe
              </label>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span>Độ phân giải: <strong>640x480</strong></span>
              <span>•</span>
              <span>Target: <strong>{targetFps} FPS</strong></span>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Real-time Telemetry, AI Prediction & Sentence Builder (5 Cols) */}
        <div className="lg:col-span-5 space-y-5">
          {/* 1. REAL-TIME TELEMETRY & LATENCY BENCHMARK CARD */}
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Gauge className="w-5 h-5 text-brand-400" />
                <h3 className="font-semibold text-white text-sm tracking-wide uppercase">
                  Đo Lường Độ Trễ Real-time (Telemetry)
                </h3>
              </div>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
                Micro-benchmark
              </span>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {/* E2E Latency */}
              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80">
                <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>E2E RTT</span>
                </div>
                <div className="text-lg font-mono font-bold text-white">
                  {telemetry.e2eLatency} <span className="text-xs font-normal text-slate-400">ms</span>
                </div>
              </div>

              {/* Server AI Infer */}
              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80">
                <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
                  <Cpu className="w-3.5 h-3.5 text-brand-400" />
                  <span>AI Infer</span>
                </div>
                <div className="text-lg font-mono font-bold text-brand-400">
                  {telemetry.serverInfer} <span className="text-xs font-normal text-slate-400">ms</span>
                </div>
              </div>

              {/* MediaPipe Preprocess */}
              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80">
                <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
                  <Activity className="w-3.5 h-3.5 text-sky-400" />
                  <span>MediaPipe</span>
                </div>
                <div className="text-lg font-mono font-bold text-sky-400">
                  {telemetry.serverPreprocess} <span className="text-xs font-normal text-slate-400">ms</span>
                </div>
              </div>

              {/* Network Jitter */}
              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80">
                <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
                  <Wifi className="w-3.5 h-3.5 text-purple-400" />
                  <span>Network</span>
                </div>
                <div className="text-lg font-mono font-bold text-purple-400">
                  {telemetry.networkLatency} <span className="text-xs font-normal text-slate-400">ms</span>
                </div>
              </div>
            </div>

            {/* Real-time Latency Sparkline Graph */}
            <div className="space-y-1.5 pt-1">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Biểu đồ biến thiên độ trễ (30 frames gần nhất):</span>
                <span className="font-mono text-slate-300">Avg: {Math.round(latencyHistory.reduce((a, b) => a + b, 0) / (latencyHistory.length || 1))} ms</span>
              </div>
              <div className="h-10 w-full bg-slate-950 rounded-lg p-1.5 flex items-end gap-1 border border-slate-800">
                {latencyHistory.map((val, idx) => {
                  const max = Math.max(100, ...latencyHistory);
                  const heightPct = Math.min(100, Math.max(15, (val / max) * 100));
                  const bg = val < 35 ? 'bg-emerald-500' : val < 70 ? 'bg-amber-500' : 'bg-rose-500';
                  return (
                    <div
                      key={idx}
                      className={`flex-1 rounded-sm transition-all duration-150 ${bg}`}
                      style={{ height: `${heightPct}%` }}
                      title={`${val} ms`}
                    />
                  );
                })}
              </div>
            </div>
          </div>

          {/* 2. LIVE PREDICTION & CANDIDATES CARD */}
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Từ VSL Nhận Diện</span>
              <span
                className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${
                  isSigning
                    ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40 glow-active'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                {isSigning ? '🟢 Đang Ký Hiệu' : '⚪ Chờ Ký Hiệu...'}
              </span>
            </div>

            {/* Big Detected Word Display */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800/80 flex items-center justify-between">
              <div>
                <div className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                  {prediction !== '...' ? `"${prediction}"` : '...'}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  Độ tin cậy: <strong className="text-brand-400 font-mono">{(confidence * 100).toFixed(1)}%</strong>
                </div>
              </div>

              {prediction !== '...' && (
                <button
                  onClick={() => speakText(prediction)}
                  className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                  title="Phát âm tiếng Việt"
                >
                  <Volume2 className="w-5 h-5 text-brand-400" />
                </button>
              )}
            </div>

            {/* Top-5 Probability Bars */}
            {top5Candidates.length > 0 && (
              <div className="space-y-2 pt-1">
                <span className="text-xs font-medium text-slate-400">Top 5 Xác Suất Ứng Viên:</span>
                <div className="space-y-2">
                  {top5Candidates.map((cand, idx) => {
                    const pct = Math.round(cand.confidence * 100);
                    return (
                      <div key={idx} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-300 font-medium">
                            {idx + 1}. {cand.gloss}
                          </span>
                          <span className="font-mono text-slate-400">{pct}%</span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              idx === 0 ? 'bg-brand-500' : 'bg-slate-600'
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* 3. CONTINUOUS SENTENCE BUILDER */}
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-white text-sm">Câu Dịch Hoàn Chỉnh (Continuous SLR)</h4>
              <div className="flex items-center gap-1">
                <button
                  onClick={handleCopySentence}
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors text-xs flex items-center gap-1"
                  title="Sao chép câu"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Đã sao chép' : 'Copy'}</span>
                </button>
                <button
                  onClick={() => speakText(accumulatedSentence.join(' '))}
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors text-xs flex items-center gap-1"
                  title="Đọc toàn bộ câu"
                >
                  <Volume2 className="w-3.5 h-3.5 text-brand-400" />
                  <span>Đọc câu</span>
                </button>
              </div>
            </div>

            {/* Sentence Text Box */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 min-h-[75px] max-h-[120px] overflow-y-auto text-sm text-slate-200 leading-relaxed font-medium">
              {accumulatedSentence.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {accumulatedSentence.map((word, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded-md bg-brand-500/15 text-brand-300 border border-brand-500/20 text-xs font-semibold"
                    >
                      {word}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-slate-500 italic text-xs">
                  (Chưa có từ nào được ghi nhận. Hãy thực hiện ký hiệu trước camera để tự động ghép câu...)
                </span>
              )}
            </div>

            {/* Neural Translation Result Box */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase font-semibold text-brand-400 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" />
                  Dịch Câu Tự Nhiên (ViT5 AI Translation)
                </span>
                {translatedText && (
                  <button
                    onClick={() => speakText(translatedText)}
                    className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1"
                    title="Đọc câu dịch tiếng Việt"
                  >
                    <Volume2 className="w-3.5 h-3.5" />
                    <span>Đọc câu dịch</span>
                  </button>
                )}
              </div>
              <div className="text-sm font-medium text-white min-h-[30px] flex items-center">
                {translatedText ? (
                  <span className="text-emerald-300 font-semibold">{translatedText}</span>
                ) : (
                  <span className="text-slate-500 italic text-xs">
                    (Bản dịch tiếng Việt tự nhiên sẽ tự động xuất hiện tại đây khi ghép từ...)
                  </span>
                )}
              </div>
              {oovWarning && (
                <div className="text-[11px] text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-1 rounded-md flex items-center gap-1">
                  <AlertCircle className="w-3 h-3 shrink-0" />
                  <span>{oovWarning}</span>
                </div>
              )}
            </div>

            {/* Sentence Action Buttons */}
            <div className="flex items-center justify-between gap-2 pt-1">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setAccumulatedSentence([]);
                    setTranslatedText('');
                    setOovWarning(null);
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                  Xóa Hết
                </button>
                <button
                  onClick={() => setAccumulatedSentence((prev) => prev.slice(0, -1))}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Xóa Từ Cuối
                </button>
              </div>

              <button
                onClick={handleSaveToHistory}
                disabled={accumulatedSentence.length === 0}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold transition-colors shadow-sm"
              >
                Lưu Lịch Sử
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* BOTTOM COLLAPSIBLE CONFIGURATION PANEL */}
      <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex items-center gap-2 text-white font-medium text-sm">
          <Sliders className="w-4 h-4 text-brand-400" />
          <span>Cấu Hình Tinh Chỉnh Pipeline Thời Gian Thực</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs text-slate-300">
          {/* Confidence Slider */}
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Ngưỡng Tin Cậy (Confidence Threshold):</span>
              <strong className="font-mono text-brand-400">{(confidenceThreshold * 100).toFixed(0)}%</strong>
            </div>
            <input
              type="range"
              min="0.4"
              max="0.95"
              step="0.05"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
              className="w-full accent-brand-500 cursor-pointer"
            />
            <p className="text-[11px] text-slate-500">Chỉ chấp nhận từ khi xác suất dự đoán $\ge$ ngưỡng này.</p>
          </div>

          {/* Debounce Cooldown Slider */}
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Giãn Cách Lặp Từ (Debounce Cooldown):</span>
              <strong className="font-mono text-brand-400">{debounceSec.toFixed(1)} s</strong>
            </div>
            <input
              type="range"
              min="0.5"
              max="3.0"
              step="0.1"
              value={debounceSec}
              onChange={(e) => setDebounceSec(parseFloat(e.target.value))}
              className="w-full accent-brand-500 cursor-pointer"
            />
            <p className="text-[11px] text-slate-500">Thời gian nghỉ tối thiểu trước khi ghi nhận lại cùng 1 từ.</p>
          </div>

          {/* Sliding Window Slider */}
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Cửa Sổ Trượt (Sliding Window):</span>
              <strong className="font-mono text-brand-400">{windowSec.toFixed(1)} s</strong>
            </div>
            <input
              type="range"
              min="1.0"
              max="3.0"
              step="0.2"
              value={windowSec}
              onChange={(e) => setWindowSec(parseFloat(e.target.value))}
              className="w-full accent-brand-500 cursor-pointer"
            />
            <p className="text-[11px] text-slate-500">Thời gian thu thập chuỗi cử chỉ để nội suy về 60 frames.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
