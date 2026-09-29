import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Camera, CameraOff, Eye, EyeOff } from 'lucide-react';
import { nowMs } from '../lib/ws';

/**
 * CameraCapture Component ("Ký từ", /ws/live-stream protocol_version 2)
 * Captures webcam frames onto a canvas (NOT mirrored: the mirror is display-only CSS, as in training) and sends
 * each one as JSON {image: JPEG data URL, timestamp} over the WebSocket returned by getSocket().
 * - timestamp = nowMs() (performance clock, monotonic): the harmonized path requires strictly increasing client
 *   timestamps, and sign_result.metrics.trigger_client_timestamp lets the client measure end-to-end latency.
 * - Frames always carry a timestamp (no binary mode): a session must not mix frames with and without timestamps.
 * - getSocket() is read at every tick, so a reconnected socket is used (no stale socket captured at render time).
 */
export default function CameraCapture({
  getSocket,
  isConnected,
  targetFps = 25,
  jpegQuality = 0.75,
  drawSkeleton = true,
  landmarks = null,
  onFpsUpdate,
  onError,
}) {
  const [isActive, setIsActive] = useState(false);
  const [showOverlay, setShowOverlay] = useState(drawSkeleton);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const overlayRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const frameCountRef = useRef(0);
  const fpsTimerRef = useRef(nowMs());
  const tickRef = useRef(null);

  // 1. Draw MediaPipe skeleton keypoints onto overlay canvas
  const renderSkeleton = useCallback(() => {
    const canvas = overlayRef.current;
    if (!canvas || !showOverlay || !landmarks) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const w = canvas.width;
    const h = canvas.height;
    const { pose = [], left_hand = [], right_hand = [] } = landmarks;

    // A. Upper Body Pose (Sky Blue)
    if (pose.length > 0) {
      ctx.fillStyle = '#38bdf8';
      ctx.strokeStyle = '#0284c7';
      ctx.lineWidth = 2;
      pose.forEach(([x, y]) => {
        if (x > 0 && y > 0 && !isNaN(x) && !isNaN(y)) {
          ctx.beginPath();
          ctx.arc(x * w, y * h, 3.5, 0, 2 * Math.PI);
          ctx.fill();
        }
      });
    }

    // B. Left Hand (Emerald Green)
    if (left_hand.length > 0) {
      ctx.fillStyle = '#22c55e';
      left_hand.forEach(([x, y]) => {
        if (x > 0 && y > 0 && !isNaN(x) && !isNaN(y)) {
          ctx.beginPath();
          ctx.arc(x * w, y * h, 4, 0, 2 * Math.PI);
          ctx.fill();
        }
      });
    }

    // C. Right Hand (Purple / Cyan)
    if (right_hand.length > 0) {
      ctx.fillStyle = '#a855f7';
      right_hand.forEach(([x, y]) => {
        if (x > 0 && y > 0 && !isNaN(x) && !isNaN(y)) {
          ctx.beginPath();
          ctx.arc(x * w, y * h, 4, 0, 2 * Math.PI);
          ctx.fill();
        }
      });
    }
  }, [landmarks, showOverlay]);

  useEffect(() => {
    renderSkeleton();
  }, [landmarks, renderSkeleton]);

  // 2. Frame capture and send (one tick of the capture timer)
  const grabAndSendFrame = useCallback(() => {
    const ws = getSocket ? getSocket() : null;
    if (!videoRef.current || !canvasRef.current || !ws) return;
    if (ws.readyState !== WebSocket.OPEN) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video.videoWidth === 0 || video.videoHeight === 0) return;

    // Resize canvas to match video stream if needed
    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      if (overlayRef.current) {
        overlayRef.current.width = video.videoWidth;
        overlayRef.current.height = video.videoHeight;
      }
    }

    // Guard: skip capture if the socket buffer is backed up
    if (ws.bufferedAmount && ws.bufferedAmount > 65536) return;

    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Client FPS (frames actually sent)
    const now = nowMs();
    frameCountRef.current += 1;
    const elapsed = now - fpsTimerRef.current;
    if (elapsed >= 1000) {
      if (onFpsUpdate) onFpsUpdate(Math.round((frameCountRef.current * 1000) / elapsed));
      frameCountRef.current = 0;
      fpsTimerRef.current = now;
    }

    const dataUrl = canvas.toDataURL('image/jpeg', jpegQuality);
    ws.send(JSON.stringify({ image: dataUrl, timestamp: nowMs() }));
  }, [getSocket, jpegQuality, onFpsUpdate]);

  // the timer always calls the latest grabAndSendFrame
  useEffect(() => {
    tickRef.current = grabAndSendFrame;
  }, [grabAndSendFrame]);

  // 3. Start Webcam
  const startCamera = async () => {
    try {
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

      setIsActive(true);

      // Start capture timer
      const intervalMs = Math.round(1000 / targetFps);
      timerRef.current = setInterval(() => {
        if (tickRef.current) tickRef.current();
      }, intervalMs);
    } catch (err) {
      console.error('Camera access error:', err);
      if (onError) onError('Không thể truy cập camera. Vui lòng cấp quyền sử dụng camera trong trình duyệt.');
    }
  };

  // 4. Stop Webcam
  const stopCamera = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (overlayRef.current) {
      const ctx = overlayRef.current.getContext('2d');
      ctx.clearRect(0, 0, overlayRef.current.width, overlayRef.current.height);
    }
    setIsActive(false);
  };

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl flex flex-col">
      {/* Header Bar */}
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Camera className="w-5 h-5 text-brand-400" />
          <h2 className="text-sm font-semibold text-white">Camera Capture (Webcam)</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-1 text-xs font-mono rounded bg-slate-800 text-slate-300 border border-slate-700"
                title="Frame gửi dạng JPEG (data URL) kèm timestamp của client">
            JPEG {Math.round(jpegQuality * 100)}
          </span>

          {/* Skeleton Overlay Toggle */}
          <button
            onClick={() => setShowOverlay((prev) => !prev)}
            className={`p-1.5 rounded-lg border text-xs transition-colors ${
              showOverlay
                ? 'bg-brand-500/20 text-brand-400 border-brand-500/40'
                : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'
            }`}
            title="Bật/tắt hiển thị khung xương MediaPipe"
          >
            {showOverlay ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Video Viewport Container */}
      <div className="relative aspect-video bg-slate-950 rounded-xl overflow-hidden border border-slate-800/80 flex items-center justify-center">
        {/* Hidden internal capture canvas (never mirrored) */}
        <canvas ref={canvasRef} className="hidden" />

        {/* Live Camera Video (mirrored for display only) */}
        <video
          ref={videoRef}
          playsInline
          muted
          className={`w-full h-full object-cover transform -scale-x-100 ${
            isActive ? 'block' : 'hidden'
          }`}
        />

        {/* HTML5 Skeleton Overlay Canvas */}
        <canvas
          ref={overlayRef}
          className={`absolute inset-0 w-full h-full pointer-events-none transform -scale-x-100 ${
            isActive && showOverlay ? 'block' : 'hidden'
          }`}
        />

        {/* Placeholder when Camera is Off */}
        {!isActive && (
          <div className="flex flex-col items-center justify-center gap-3 p-6 text-center text-slate-500">
            <div className="w-16 h-16 rounded-full bg-slate-900 flex items-center justify-center border border-slate-800">
              <CameraOff className="w-8 h-8 text-slate-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-300">Camera đang tắt</p>
              <p className="text-xs text-slate-500 mt-1">
                Nhấn nút "Bật Camera" bên dưới để bắt đầu gửi frame tới backend
              </p>
            </div>
          </div>
        )}

        {/* Live Status Badge on Viewport */}
        {isActive && (
          <div className="absolute top-3 left-3 flex items-center gap-2 bg-slate-950/80 backdrop-blur-md px-2.5 py-1 rounded-full border border-slate-800 text-xs">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
            <span className="text-white font-medium">LIVE</span>
            <span className="text-slate-400 font-mono">| mục tiêu {targetFps} FPS</span>
          </div>
        )}
      </div>

      {/* Camera Controls */}
      <div className="mt-4 flex items-center justify-between gap-3">
        {!isActive ? (
          <button
            data-testid="camera-start"
            onClick={startCamera}
            disabled={!isConnected}
            className={`w-full py-2.5 px-4 rounded-xl font-medium text-sm flex items-center justify-center gap-2 transition-all shadow-lg ${
              isConnected
                ? 'bg-brand-600 hover:bg-brand-500 text-white shadow-brand-600/20'
                : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
            }`}
          >
            <Camera className="w-4 h-4" />
            <span>{isConnected ? 'Bật Camera & Bắt đầu Dịch' : 'Chờ Kết nối WebSocket...'}</span>
          </button>
        ) : (
          <button
            data-testid="camera-stop"
            onClick={stopCamera}
            className="w-full py-2.5 px-4 rounded-xl font-medium text-sm bg-rose-600/90 hover:bg-rose-500 text-white flex items-center justify-center gap-2 transition-all shadow-lg shadow-rose-600/20"
          >
            <CameraOff className="w-4 h-4" />
            <span>Dừng Camera</span>
          </button>
        )}
      </div>
    </div>
  );
}
