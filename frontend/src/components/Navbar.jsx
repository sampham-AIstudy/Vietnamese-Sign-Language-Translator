import React from 'react';
import { Activity, BookOpen, Layers, Sparkles, Video, Wifi, WifiOff } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, systemStatus }) {
  const isAiOnline = systemStatus?.python_ai_engine?.status === 'online';
  const isNodeOnline = systemStatus?.node_server === 'online';

  const navItems = [
    { id: 'realtime', label: 'Nhận diện Thời Gian Thực', icon: Video, badge: 'Live Stream' },
    { id: 'alphabet', label: 'Bảng Chữ Cái', icon: Sparkles, badge: 'Level 1' },
    { id: 'dictionary', label: 'Từ Điển 3 Miền', icon: BookOpen, badge: '4,362 Video' },
    { id: 'reports', label: 'Kiến Trúc & Báo Cáo', icon: Layers, badge: 'Paper 1 & 2' },
  ];

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-emerald-400 flex items-center justify-center shadow-lg shadow-brand-500/20 text-xl">
              🤟
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-white tracking-tight">VSL Translator</span>
                <span className="px-2 py-0.5 text-xs font-semibold bg-brand-500/20 text-brand-400 border border-brand-500/30 rounded-full">
                  Real-time AI
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">Hệ thống Dịch Ngôn ngữ Ký hiệu Việt Nam</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1 sm:gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-slate-800 text-white shadow-inner border border-slate-700'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-brand-400' : 'text-slate-400'}`} />
                  <span className="hidden md:inline">{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Microservices Status Indicator */}
          <div className="hidden lg:flex items-center gap-3 text-xs bg-slate-950/60 border border-slate-800 rounded-lg px-3 py-1.5">
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${isNodeOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
              <span className="text-slate-400">Node API:</span>
              <span className={isNodeOnline ? 'text-emerald-400 font-medium' : 'text-rose-400 font-medium'}>
                {isNodeOnline ? ':5000' : 'Offline'}
              </span>
            </div>
            <div className="w-px h-3.5 bg-slate-800" />
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${isAiOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
              <span className="text-slate-400">Python AI:</span>
              <span className={isAiOnline ? 'text-emerald-400 font-medium' : 'text-rose-400 font-medium'}>
                {isAiOnline ? ':8000' : 'Offline'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
