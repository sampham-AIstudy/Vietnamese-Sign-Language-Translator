import React, { useState } from 'react';
import {
  Activity,
  Clock,
  Volume2,
  Copy,
  Trash2,
  Undo2,
  Wifi,
  WifiOff,
  AlertCircle,
  Zap,
  Layers,
  Check,
} from 'lucide-react';

/**
 * PredictionDisplay Component ("Ký từ")
 * Renders what the server sent: top-1 gloss + model confidence, top-5 candidates, telemetry, status and the word
 * list. Every value comes from a /ws/live-stream message (frame_result on the legacy path, sign_result on the
 * harmonized_v1 path); nothing is computed or invented here.
 */
export default function PredictionDisplay({
  gloss = null,
  confidence = null,
  status = 'IDLE', // legacy: IDLE | DETECTING | CONFIRMED; harmonized_v1: IDLE | RECORDING | WAIT_REST
  top5 = [],
  fps = null,
  latencyMs = null,
  connectionStatus = 'disconnected', // 'disconnected' | 'connecting' | 'connected' | 'error'
  errorMessage = '',
  sentence = [],
  onClearSentence,
  onUndoWord,
  onSpeakSentence,
  bufferFill = null,
  bufferCapacity = null,
  resultLabel = 'Từ Nhận Diện (Top-1 Gloss)',
}) {
  const [copied, setCopied] = useState(false);
  const hasConfidence = typeof confidence === 'number' && Number.isFinite(confidence);

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
      case 'RECORDING':
        return {
          bg: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
          dot: 'bg-rose-400 animate-pulse',
          text: 'Đang ghi ký hiệu',
        };
      case 'WAIT_REST':
        return {
          bg: 'bg-amber-500/20 text-amber-400 border-amber-500/40',
          dot: 'bg-amber-400',
          text: 'Chờ hạ tay',
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
            WebSocket đã kết nối
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
        <div className="flex items-center gap-2" data-testid="live-connection" data-status={connectionStatus}>
          {getConnectionBadge()}
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
          <div className="flex items-center gap-1.5" title="Thời gian xử lý phía server của frame gần nhất">
            <Clock className="w-3.5 h-3.5 text-brand-400" />
            <span>Server: </span>
            <span className="text-white font-semibold">{latencyMs ?? '—'} ms</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-emerald-400" />
            <span>Tốc độ: </span>
            <span className="text-white font-semibold">{fps ?? '—'} FPS</span>
          </div>
          {bufferCapacity !== null && (
            <div className="hidden sm:flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              <span>Buffer: </span>
              <span className="text-white font-semibold">{bufferFill ?? 0}/{bufferCapacity}</span>
            </div>
          )}
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
        {status === 'CONFIRMED' && (
          <div className="absolute -right-12 -top-12 w-36 h-36 bg-emerald-500/10 rounded-full blur-2xl pointer-events-none" />
        )}

        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            {resultLabel}
          </span>
          <span data-testid="live-status" data-status={status}
                className={`px-2.5 py-0.5 rounded-full text-xs font-medium border flex items-center gap-1.5 ${statusBadge.bg}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${statusBadge.dot}`} />
            {statusBadge.text}
          </span>
        </div>

        {/* Large Gloss Text (exactly the gloss sent by the server) */}
        <div className="my-3">
          <div data-testid="live-gloss" className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            {gloss || '...'}
          </div>
        </div>

        {/* Model confidence */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-slate-400">Độ tin cậy của mô hình</span>
            <span data-testid="live-confidence" data-value={hasConfidence ? String(confidence) : ''}
                  className="font-mono font-bold text-brand-400">
              {hasConfidence ? `${(confidence * 100).toFixed(1)}%` : '—'}
            </span>
          </div>
          <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-200 rounded-full ${
                hasConfidence && confidence >= 0.7
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
                  : hasConfidence && confidence >= 0.4
                  ? 'bg-gradient-to-r from-amber-500 to-yellow-400'
                  : 'bg-slate-700'
              }`}
              style={{ width: `${hasConfidence ? Math.min(100, Math.max(0, confidence * 100)) : 0}%` }}
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

        <div className="space-y-2" data-testid="live-top5">
          {top5.length === 0 ? (
            <div className="py-4 text-center text-xs text-slate-500">
              Chưa có dự đoán từ mô hình
            </div>
          ) : (
            top5.slice(0, 5).map((item, idx) => {
              const itemGloss = typeof item === 'object' && !Array.isArray(item) ? item.gloss : item[0];
              const itemConf = typeof item === 'object' && !Array.isArray(item) ? item.confidence : item[1];
              const isTop1 = idx === 0;

              return (
                <div key={idx} className="flex items-center gap-3 text-xs" data-testid="live-top5-item"
                     data-gloss={itemGloss} data-confidence={String(itemConf)}>
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

      {/* 4. Word list (every word reported by the server, in order) */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Các từ đã nhận
          </span>
          <div className="flex items-center gap-1.5">
            <button
              data-testid="live-undo"
              onClick={onUndoWord}
              disabled={sentence.length === 0}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed text-xs transition-colors"
              title="Xóa từ cuối"
            >
              <Undo2 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onSpeakSentence && onSpeakSentence(sentence.join(' '))}
              disabled={sentence.length === 0}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed text-xs transition-colors"
              title="Đọc to (TTS)"
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
              title="Xóa hết"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div data-testid="live-words"
             className="min-h-[52px] p-3 rounded-xl bg-slate-950 border border-slate-800/80 flex flex-wrap items-center gap-1.5">
          {sentence.length === 0 ? (
            <span className="text-xs text-slate-500 italic">
              Các từ server nhận ra sẽ hiện tại đây (không gộp, không khử trùng)...
            </span>
          ) : (
            sentence.map((word, i) => (
              <span
                key={i}
                data-testid="live-word"
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
