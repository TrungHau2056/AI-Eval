import React, { useState } from 'react';

interface SidebarProps {
  apiKey: string;
  aiModel: string;
  onApiKeyChange: (val: string) => void;
  onAiModelChange: (val: string) => void;
}

export default function Sidebar({ apiKey, aiModel, onApiKeyChange, onAiModelChange }: SidebarProps) {
  const [showApiKey, setShowApiKey] = useState(false);
  const [activeNav, setActiveNav] = useState('pipeline');

  const navItems = [
    { id: 'pipeline', icon: 'bolt', label: 'Pipeline' },
  ];

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-white text-stone-500 flex flex-col py-6 border-r border-black/10 z-50">
      {/* Brand */}
      <div className="px-6 mb-8">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-[#ff4d00] flex items-center justify-center text-white">
            <span className="material-symbols-outlined text-[22px] font-bold">bolt</span>
          </div>
          <div>
            <h1 className="text-stone-900 font-bold text-[17px] tracking-tight leading-tight uppercase font-sans">
              AI Eval
            </h1>
            <p className="text-[9px] text-[#ff4d00] uppercase tracking-[0.2em] font-bold mt-0.5">
              Test Case Generator
            </p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="px-3 space-y-1">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveNav(item.id)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-none text-[13px] font-semibold transition-all cursor-pointer ${
              activeNav === item.id
                ? 'bg-[#ff4d00]/10 text-stone-900 border-l-2 border-[#ff4d00]'
                : 'hover:bg-black/5 hover:text-stone-900'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
            <span className="uppercase tracking-wider text-xs">{item.label}</span>
          </button>
        ))}
      </nav>

      <hr className="border-black/10 my-6 mx-6" />

      {/* Settings */}
      <div className="px-6 space-y-4">
        <h2 className="text-[10px] font-semibold text-stone-400 uppercase tracking-[0.25em] leading-none">
          LLM Config
        </h2>

        {/* API Key */}
        <div className="space-y-1.5">
          <label className="block text-[10px] text-stone-500 uppercase tracking-widest font-bold opacity-80">
            API Key
          </label>
          <div className="relative">
            <input
              type={showApiKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => onApiKeyChange(e.target.value)}
              placeholder="Nhập API key..."
              className="w-full bg-stone-50 text-stone-900 border border-black/10 rounded-none px-3 py-2 text-xs focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all pr-8 font-mono placeholder-stone-400"
            />
            <button
              type="button"
              onClick={() => setShowApiKey(!showApiKey)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-900 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[15px] select-none">
                {showApiKey ? 'visibility' : 'visibility_off'}
              </span>
            </button>
          </div>
        </div>

        {/* Model */}
        <div className="space-y-1.5">
          <label className="block text-[10px] text-stone-500 uppercase tracking-widest font-bold opacity-80">
            Model
          </label>
          <div className="relative">
            <select
              value={aiModel}
              onChange={(e) => onAiModelChange(e.target.value)}
              className="w-full bg-stone-50 text-stone-900 border border-black/10 rounded-none px-3 py-2 text-xs focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all appearance-none cursor-pointer pr-8 font-mono"
            >
              <option value="gemini" className="bg-white">Gemini 1.5 Pro</option>
              <option value="openai" className="bg-white">GPT-4o</option>
            </select>
            <span className="material-symbols-outlined absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none text-[16px]">
              expand_more
            </span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-auto px-4 space-y-1 border-t border-black/10 pt-4">
        <a href="https://github.com/TrungHau2056/AI-Eval" target="_blank" rel="noreferrer"
          className="flex items-center gap-3 px-4 py-2 rounded-none text-[12px] text-stone-500 hover:bg-black/5 hover:text-stone-900 transition-all cursor-pointer"
        >
          <span className="material-symbols-outlined text-[18px]">code</span>
          <span className="uppercase tracking-wider text-[11px]">GitHub</span>
        </a>
        <div className="px-4 pt-2 text-[9px] text-stone-400 font-mono uppercase tracking-widest">
          AI-Eval · ui-khanh branch
        </div>
      </div>
    </aside>
  );
}
