import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import RealtimeStream from './components/RealtimeStream';
import Fingerspelling from './components/Fingerspelling';
import Dictionary from './components/Dictionary';
import Reports from './components/Reports';

export default function App() {
  const [activeTab, setActiveTab] = useState('realtime');
  const [systemStatus, setSystemStatus] = useState(null);

  // Check health of backend microservices periodically
  const checkStatus = async () => {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        setSystemStatus(data);
      }
    } catch (err) {
      setSystemStatus({ node_server: 'offline', python_ai_engine: { status: 'offline' } });
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSaveHistory = async (text, confidence, words) => {
    try {
      await fetch('/api/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, confidence, words }),
      });
    } catch (err) {
      console.error('Failed saving translation history:', err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-brand-500 selection:text-white">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'realtime' && <RealtimeStream onSaveHistory={handleSaveHistory} />}
        {activeTab === 'alphabet' && <Fingerspelling />}
        {activeTab === 'dictionary' && <Dictionary />}
        {activeTab === 'reports' && <Reports />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>VSL Translator • Vietnamese Sign Language Recognition Pipeline</span>
          <span className="text-slate-600">Fullstack React + Node.js + FastAPI • Laptop RTX 3050 Optimized</span>
        </div>
      </footer>
    </div>
  );
}
