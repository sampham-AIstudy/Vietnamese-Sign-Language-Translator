import React, { useState, useEffect, useRef, useCallback } from 'react';
import CameraCapture from './CameraCapture';
import PredictionDisplay from './PredictionDisplay';
import { Wifi, RefreshCw, Sparkles, Send } from 'lucide-react';

/**
 * Phase12Pipeline Container Component
 * Coordinates WebSocket connection with FastAPI backend (:8000/ws/live-stream),
 * connects CameraCapture (frame acquisition) and PredictionDisplay (results HUD).
 */
export default function Phase12Pipeline() {
  const [connectionStatus, setConnectionStatus] = useState('disconnected'); // 'disconnected' | 'connecting' | 'connected' | 'error'
  const [errorMessage, setErrorMessage] = useState('');

  // Recognition Results from Backend
  const [gloss, setGloss] = useState('...');
  const [confidence, setConfidence] = useState(0.0);
  const [status, setStatus] = useState('IDLE');
  const [top5, setTop5] = useState([]);
  const [fps, setFps] = useState(0);
  const [latencyMs, setLatencyMs] = useState(0);
  const [bufferFill, setBufferFill] = useState(0);
  const [sentence, setSentence] = useState([]);
  const [landmarks, setLandmarks] = useState(null);

  const wsRef = useRef(null);

  // Text to Speech
  const speakText = (text) => {
    if (!text || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'vi-VN';
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('TTS error:', e);
    }
  };

  // Connect WebSocket
  const connectWs = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    setConnectionStatus('connecting');
    setErrorMessage('');

    const host = window.location.hostname || 'localhost';
    const wsUrl = `ws://${host}:8000/ws/live-stream`;
    console.log(`[WS] Connecting to ${wsUrl}...`);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WS] Connected to FastAPI backend!');
        setConnectionStatus('connected');
        setErrorMessage('');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Update recognition state according to Phase 12 Schema:
          // {"gloss": "...", "confidence": 0.0, "top5": [], "latency_ms": 0, "fps": 0, "status": "..."}
          if (data.gloss !== undefined) setGloss(data.gloss);
          if (data.confidence !== undefined) setConfidence(data.confidence);
          if (data.status !== undefined) setStatus(data.status);
          if (data.top5 !== undefined) setTop5(data.top5);
          if (data.latency_ms !== undefined) setLatencyMs(data.latency_ms);
          if (data.fps !== undefined) setFps(data.fps);
          if (data.buffer_fill !== undefined) setBufferFill(data.buffer_fill);
          if (data.landmarks) setLandmarks(data.landmarks);

          // If confirmed word received, append to sentence
          if (data.status === 'CONFIRMED' && data.gloss && data.gloss !== '...') {
            setSentence((prev) => {
              if (prev[prev.length - 1] !== data.gloss) {
                speakText(data.gloss);
                return [...prev, data.gloss];
              }
              return prev;
            });
          }
        } catch (err) {
          console.error('[WS] Failed to parse message:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('[WS] Connection error:', err);
        setConnectionStatus('error');
        setErrorMessage('Không thể kết nối tới FastAPI Backend (ws://localhost:8000/ws/live-stream). Vui lòng khởi động backend.');
      };

      ws.onclose = () => {
        console.log('[WS] Connection closed.');
        setConnectionStatus('disconnected');
      };
    } catch (err) {
      console.error('[WS] Initialization failed:', err);
      setConnectionStatus('error');
      setErrorMessage(`Lỗi khởi tạo WebSocket: ${err.message}`);
    }
  }, []);

  useEffect(() => {
    connectWs();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWs]);

  // Send a synthetic test frame for smoke testing
  const sendTestFrame = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      alert('WebSocket chưa kết nối!');
      return;
    }

    // 1x1 transparent JPEG
    const testBase64 = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=';
    wsRef.current.send(JSON.stringify({ image: testBase64, timestamp: Date.now() }));
  };

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 bg-slate-900 border border-slate-800 rounded-2xl">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand-500/20 text-brand-400 border border-brand-500/30">
              PHASE 12
            </span>
            <h1 className="text-base font-bold text-white">FastAPI + React Production Realtime Pipeline</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Giao diện Web nhận diện Ngôn ngữ Ký hiệu Việt Nam thời gian thực qua WebSocket
          </p>
        </div>

        <div className="flex items-center gap-2">
          {connectionStatus !== 'connected' && (
            <button
              onClick={connectWs}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-brand-600 hover:bg-brand-500 text-white transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Thử Kết Nối Lại</span>
            </button>
          )}

          <button
            onClick={sendTestFrame}
            disabled={connectionStatus !== 'connected'}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-50 transition-colors border border-slate-700"
            title="Gửi 1 frame kiểm thử để test phản hồi của Backend"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Test Frame</span>
          </button>
        </div>
      </div>

      {/* Main 2-Column Responsive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: CameraCapture Component (7 cols) */}
        <div className="lg:col-span-7">
          <CameraCapture
            ws={wsRef.current}
            isConnected={connectionStatus === 'connected'}
            targetFps={25}
            drawSkeleton={true}
            landmarks={landmarks}
            onError={(msg) => setErrorMessage(msg)}
          />
        </div>

        {/* Right Column: PredictionDisplay Component (5 cols) */}
        <div className="lg:col-span-5">
          <PredictionDisplay
            gloss={gloss}
            confidence={confidence}
            status={status}
            top5={top5}
            fps={fps}
            latencyMs={latencyMs}
            connectionStatus={connectionStatus}
            errorMessage={errorMessage}
            sentence={sentence}
            onClearSentence={() => setSentence([])}
            onSpeakSentence={speakText}
            bufferFill={bufferFill}
            bufferCapacity={60}
          />
        </div>
      </div>
    </div>
  );
}
