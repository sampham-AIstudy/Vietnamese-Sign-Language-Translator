import React, { useState } from 'react';
import {
  Activity,
  CheckCircle2,
  Clock,
  Volume2,
  Copy,
  Trash2,
  Wifi,
  WifiOff,
  AlertCircle,
  Zap,
  Layers,
  Check,
} from 'lucide-react';

/**
 * PredictionDisplay Component (Phase 12)
 * Renders real-time sign language predictions, top-5 candidates,
 * telemetry metrics (FPS, Latency), status badges, and sentence history.
 */
export default function PredictionDisplay({
  gloss = '...',
  confidence = 0.0,
  status = 'IDLE', // 'IDLE' | 'DETECTING' | 'CONFIRMED'
  top5 = [],
  fps = 0,
  latencyMs = 0,
  connectionStatus = 'disconnected', // 'disconnected' | 'connecting' | 'connected' | 'error'
  errorMessage = '',
  sentence = [],
  onClearSentence,
  onSpeakSentence,
  bufferFill = 0,
  bufferCapacity = 60,
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (sentence.length === 0) return;
    navigator.clipboard.writeText(sentence.join(' '));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Status badge style configuration
  const getStatusBadge = () => {
    switch (status) {
      case 'CONFIRMED':
        return {
          bg: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40',
          dot: 'bg-emerald-400 animate-pulse',
          text: 'Đã xác nhận',
        };
      case 'DETECTING':
        return {
          bg: 'bg-amber-500/20 text-amber-400 border-amber-500/40',
          dot: 'bg-amber-400 animate-ping',
          text: 'Đang nhận diện...',
        };
      case 'IDLE':
      default:
        return {
          bg: 'bg-slate-800 text-slate-400 border-slate-700',
          dot: 'bg-slate-500',
          text: 'Chờ cử chỉ',
        };
    }
  };

  const statusBadge = getStatusBadge();

  // Connection badge config
  const getConnectionBadge = () => {
    switch (connectionStatus) {
      case 'connected':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <Wifi className="w-3.5 h-3.5" />
            WebSocket Online (:8000)
          </span>
        );
      case 'connecting':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            Đang kết nối...
          </span>
        );
      case 'error':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/30">
            <WifiOff className="w-3.5 h-3.5" />
            Mất kết nối
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
            <WifiOff className="w-3.5 h-3.5" />
            Chưa kết nối
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* 1. Connection & Performance Telemetry Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {getConnectionBadge()}
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-brand-400" />
            <span>Độ trễ: </span>
            <span className="text-white font-semibold">{latencyMs} ms</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-emerald-400" />
            <span>Tốc độ: </span>
            <span className="text-white font-semibold">{fps} FPS</span>
          </div>
          <div className="hidden sm:flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-purple-400" />
            <span>Buffer: </span>
            <span className="text-white font-semibold">{bufferFill}/{bufferCapacity}</span>
          </div>
        </div>
      </div>

      {/* Connection Error Message */}
      {errorMessage && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-3 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* 2. Primary Recognition Result Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl relative overflow-hidden">
        {/* Background glow when confirmed */}
        {status === 'CONFIRMED' && (
          <div className="absolute -right-12 -top-12 w-36 h-36 bg-emerald-500/10 rounded-full blur-2xl pointer-events-none" />
        )}

        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Từ Nhận Diện (Top-1 Gloss)
          </span>
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border flex items-center gap-1.5 ${statusBadge.bg}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${statusBadge.dot}`} />
            {statusBadge.text}
          </span>
        </div>

        {/* Large Gloss Text */}
        <div className="my-3">
          <div className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight capitalize">
            {gloss !== '...' ? gloss : '...'}
          </div>
        </div>

        {/* Confidence Gauge Bar */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-slate-400">Độ Tin Cậy (Confidence)</span>
            <span className="font-mono font-bold text-brand-400">
              {(confidence * 100).toFixed(1)}%
            </span>
          </div>
          <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-200 rounded-full ${
                confidence >= 0.7
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
                  : confidence >= 0.4
                  ? 'bg-gradient-to-r from-amber-500 to-yellow-400'
                  : 'bg-slate-700'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, confidence * 100))}%` }}
            />
          </div>
        </div>
      </div>

      {/* 3. Top-5 Prediction Candidates */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-brand-400" />
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Top 5 Dự Đoán Cao Nhất
            </h3>
          </div>
        </div>

        <div className="space-y-2">
          {top5.length === 0 ? (
            <div className="py-4 text-center text-xs text-slate-500">
              Chưa có dữ liệu dự đoán từ mô hình
            </div>
          ) : (
            top5.slice(0, 5).map((item, idx) => {
              const itemGloss = typeof item === 'object' ? item.gloss : item[0];
              const itemConf = typeof item === 'object' ? item.confidence : item[1];
              const isTop1 = idx === 0;

              return (
                <div key={idx} className="flex items-center gap-3 text-xs">
                  <span className={`w-5 font-mono text-center font-bold ${isTop1 ? 'text-brand-400' : 'text-slate-500'}`}>
                    #{idx + 1}
                  </span>
                  <span className={`flex-1 truncate font-medium ${isTop1 ? 'text-white' : 'text-slate-300'}`}>
                    {itemGloss}
                  </span>
                  <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${isTop1 ? 'bg-brand-500' : 'bg-slate-600'}`}
                      style={{ width: `${Math.min(100, (itemConf || 0) * 100)}%` }}
                    />
                  </div>
                  <span className="w-12 text-right font-mono text-slate-400">
                    {((itemConf || 0) * 100).toFixed(0)}%
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 4. Accumulated Sentence History */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Câu Đã Ghép (Sentence Stream)
          </span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => onSpeakSentence && onSpeakSentence(sentence.join(' '))}
              disabled={sentence.length === 0}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed text-xs transition-colors"
              title="Đọc to câu tiếng Việt (TTS)"
            >
              <Volume2 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleCopy}
              disabled={sentence.length === 0}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed text-xs transition-colors"
              title="Sao chép văn bản"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
            <button
              onClick={onClearSentence}
              disabled={sentence.length === 0}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-900/40 text-slate-300 hover:text-rose-400 disabled:opacity-40 disabled:cursor-not-allowed text-xs transition-colors"
              title="Xóa lịch sử câu"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="min-h-[52px] p-3 rounded-xl bg-slate-950 border border-slate-800/80 flex flex-wrap items-center gap-1.5">
          {sentence.length === 0 ? (
            <span className="text-xs text-slate-500 italic">
              Các từ ký hiệu được xác nhận sẽ tự động nối thành câu tại đây...
            </span>
          ) : (
            sentence.map((word, i) => (
              <span
                key={i}
                className="px-2.5 py-1 rounded-lg bg-brand-500/10 text-brand-300 border border-brand-500/20 text-xs font-medium"
              >
                {word}
              </span>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
