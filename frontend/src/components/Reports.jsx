import React from 'react';
import { Layers, Award, BarChart3, CheckCircle2, ShieldCheck, Cpu } from 'lucide-react';

export default function Reports() {
  return (
    <div className="space-y-6">
      {/* Top Architecture Comparison */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Kiến Trúc Hệ Thống & So Sánh Báo Cáo Cơ Sở</h3>
            <p className="text-xs text-slate-400">
              Tổng hợp phương pháp từ 2 bài báo nghiên cứu VSLR và kết quả thực nghiệm thực tế.
            </p>
          </div>
        </div>

        {/* Comparison Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300 border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider bg-slate-950/60">
                <th className="p-3.5 font-semibold">Thành Phần</th>
                <th className="p-3.5 font-semibold">Báo cáo 1 (Review VSLR 2026)</th>
                <th className="p-3.5 font-semibold">Báo cáo 2 (VSL Alphabet 2025)</th>
                <th className="p-3.5 font-semibold text-brand-400">Dự Án Này Triển Khai</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              <tr className="hover:bg-slate-800/30">
                <td className="p-3.5 font-bold text-white">Phạm Vi Bài Toán</td>
                <td className="p-3.5">Word-Level & Continuous SLR</td>
                <td className="p-3.5">25 Ký tự bảng chữ cái tĩnh</td>
                <td className="p-3.5 font-semibold text-brand-300">Dual-Level: Cả Chữ Cái & Từ Đơn VSL</td>
              </tr>
              <tr className="hover:bg-slate-800/30">
                <td className="p-3.5 font-bold text-white">Trích Xuất Đặc Trưng</td>
                <td className="p-3.5">MediaPipe Holistic (Pose + 2 Hands)</td>
                <td className="p-3.5">MediaPipe Hands (21 keypoints)</td>
                <td className="p-3.5 font-semibold text-brand-300">Dual Extractor: 201 chiều & 42 chiều</td>
              </tr>
              <tr className="hover:bg-slate-800/30">
                <td className="p-3.5 font-bold text-white">Không Gian Đầu Vào</td>
                <td className="p-3.5">Vector chuỗi thời gian (60, 201)</td>
                <td className="p-3.5">Vector tĩnh 42 toạ độ chuẩn hoá</td>
                <td className="p-3.5 font-semibold text-brand-300">Resampled (60, 201) tối ưu bộ nhớ RTX 3050</td>
              </tr>
              <tr className="hover:bg-slate-800/30">
                <td className="p-3.5 font-bold text-white">Kiến Trúc Mô Hình</td>
                <td className="p-3.5">BiLSTM / BiGRU / Transformer</td>
                <td className="p-3.5">Multilayer Perceptron / CNN</td>
                <td className="p-3.5 font-semibold text-brand-300">BiGRU + Attention & Spatio-Temporal Transformer</td>
              </tr>
              <tr className="hover:bg-slate-800/30">
                <td className="p-3.5 font-bold text-white">Độ Chính Xác Thực Nghiệm</td>
                <td className="p-3.5">98.13% (Pham et al.), 92.47% (Cross-Attn)</td>
                <td className="p-3.5">95.0% sau tiền xử lý</td>
                <td className="p-3.5 font-bold text-emerald-400">99.87% Top-1, 100.00% Top-5 Test Acc</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Real-time Telemetry Benchmarks Card */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
            <div className="flex items-center gap-2 text-brand-400 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4" />
              <span>Độ Trễ Suy Luận (Inference)</span>
            </div>
            <div className="text-2xl font-bold text-white font-mono">1.8 - 2.5 ms</div>
            <p className="text-[11px] text-slate-500">Mô hình BiGRU chạy trên GPU RTX 3050 / CPU x86.</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
            <div className="flex items-center gap-2 text-sky-400 text-xs font-semibold">
              <Cpu className="w-4 h-4" />
              <span>Thời Gian Trích Xuất MediaPipe</span>
            </div>
            <div className="text-2xl font-bold text-white font-mono">10 - 15 ms</div>
            <p className="text-[11px] text-slate-500">Xử lý trích xuất 201 landmark/frame 640x480.</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
            <div className="flex items-center gap-2 text-purple-400 text-xs font-semibold">
              <ShieldCheck className="w-4 h-4" />
              <span>Tổng Độ Trễ End-to-End (E2E)</span>
            </div>
            <div className="text-2xl font-bold text-emerald-400 font-mono">25 - 35 ms</div>
            <p className="text-[11px] text-slate-500">Bao gồm Camera Capture $\to$ WebSocket $\to$ AI $\to$ UI Render.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
