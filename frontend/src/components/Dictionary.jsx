import React, { useState, useEffect } from 'react';
import { BookOpen, Search, Filter, Play, ExternalLink, Globe } from 'lucide-react';

export default function Dictionary() {
  const [searchQuery, setSearchQuery] = useState('địa chỉ');
  const [selectedRegion, setSelectedRegion] = useState('All');
  const [dictionaryData, setDictionaryData] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [activeVideo, setActiveVideo] = useState(null);

  const regions = [
    { code: 'All', label: 'Tất Cả 3 Miền' },
    { code: 'B', label: 'Miền Bắc (North)' },
    { code: 'T', label: 'Miền Trung (Central)' },
    { code: 'N', label: 'Miền Nam (South)' },
  ];

  const fetchDictionary = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        q: searchQuery,
        region: selectedRegion,
        page: page.toString(),
        limit: '18',
      });
      const res = await fetch(`/api/dictionary?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setDictionaryData(data.items || []);
        setTotalCount(data.total || 0);
      }
    } catch (err) {
      console.error('Failed loading dictionary:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDictionary();
  }, [searchQuery, selectedRegion, page]);

  return (
    <div className="space-y-6">
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Tra Cứu Từ Điển & Phương Ngữ Ký Hiệu Việt Nam</h3>
              <p className="text-xs text-slate-400">
                Bộ dữ liệu thực tế gồm <strong>4,362 video</strong> gán nhãn, phản ánh đặc thù phương ngữ 3 miền Bắc (B), Trung (T), Nam (N).
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800 text-xs text-slate-300">
            <Globe className="w-4 h-4 text-brand-400" />
            <span>Tổng cộng: <strong className="text-white font-mono">{totalCount.toLocaleString()}</strong> video</span>
          </div>
        </div>

        {/* Search Bar & Region Filters */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
          <div className="md:col-span-7 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Tìm kiếm từ ký hiệu (ví dụ: 'địa chỉ', 'công an', 'thành phố', 'bác sĩ')..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          <div className="md:col-span-5 flex items-center gap-1.5 overflow-x-auto">
            {regions.map((reg) => (
              <button
                key={reg.code}
                onClick={() => {
                  setSelectedRegion(reg.code);
                  setPage(1);
                }}
                className={`px-3 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                  selectedRegion === reg.code
                    ? 'bg-brand-600 text-white shadow-md shadow-brand-500/20'
                    : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {reg.label}
              </button>
            ))}
          </div>
        </div>

        {/* Dictionary Grid */}
        {loading ? (
          <div className="py-16 text-center">
            <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <span className="text-xs text-slate-400">Đang tra cứu cơ sở dữ liệu...</span>
          </div>
        ) : dictionaryData.length === 0 ? (
          <div className="py-16 text-center bg-slate-950 rounded-xl border border-slate-800">
            <p className="text-sm text-slate-400">Không tìm thấy từ ký hiệu nào phù hợp với từ khóa.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {dictionaryData.map((item, idx) => (
              <div
                key={idx}
                onClick={() => setActiveVideo(item)}
                className="group p-3.5 rounded-xl bg-slate-950 hover:bg-slate-900 border border-slate-800/80 hover:border-brand-500/40 transition-all cursor-pointer shadow-sm hover:shadow-lg space-y-2"
              >
                <div className="flex items-center justify-between text-[11px]">
                  <span className="px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 font-mono">#{item.id}</span>
                  <span className="text-brand-400 font-medium text-[10px]">{item.region}</span>
                </div>
                <h4 className="font-bold text-white text-sm group-hover:text-brand-300 transition-colors line-clamp-1">
                  {item.label}
                </h4>
                <div className="flex items-center justify-between text-xs text-slate-500 pt-1 border-t border-slate-900">
                  <span className="text-[10px] font-mono truncate max-w-[100px]">{item.video}</span>
                  <Play className="w-3.5 h-3.5 text-brand-400 group-hover:scale-110 transition-transform" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Video Player Modal */}
        {activeVideo && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="max-w-lg w-full bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-white">Ký hiệu: "{activeVideo.label}"</h3>
                  <span className="text-xs text-brand-400">{activeVideo.region}</span>
                </div>
                <button
                  onClick={() => setActiveVideo(null)}
                  className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
                >
                  ✕
                </button>
              </div>

              <div className="rounded-xl overflow-hidden bg-black aspect-video flex items-center justify-center border border-slate-800">
                <video
                  src={`/videos/${activeVideo.video}`}
                  controls
                  autoPlay
                  className="w-full h-full object-contain"
                />
              </div>

              <div className="text-xs text-slate-400 flex justify-between">
                <span>Tên file: <code>{activeVideo.video}</code></span>
                <span>ID: #{activeVideo.id}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
