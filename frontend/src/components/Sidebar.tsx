import React, { useState } from "react";
import { CostSummary } from "../types";

interface SidebarProps {
  apiKey: string;
  domain: string;
  aiModel: string;
  onApiKeyChange: (val: string) => void;
  onDomainChange: (val: string) => void;
  onAiModelChange: (val: string) => void;
  activeSidebarTab: string;
  setActiveSidebarTab: (tab: string) => void;
  costSummary?: CostSummary | null;
  onRefreshCosts?: () => void;
  onEndCostRun?: () => void;
  onComingSoonClick?: () => void;
}

const formatUsd = (value?: number | null): string => {
  if (value === null || value === undefined) return "--";
  const digits = Math.abs(value) < 0.01 ? 6 : 4;
  return `$${value.toFixed(digits)}`;
};

const shortRunId = (runId?: string | null): string => {
  if (!runId) return "--";
  return runId.slice(0, 6);
};

export default function Sidebar({
  apiKey,
  domain,
  aiModel,
  onApiKeyChange,
  onDomainChange,
  onAiModelChange,
  activeSidebarTab,
  setActiveSidebarTab,
  costSummary,
  onRefreshCosts,
  onEndCostRun,
  onComingSoonClick
}: SidebarProps) {
  const [showApiKey, setShowApiKey] = useState(false);
  const hasCostEvents = (costSummary?.event_count ?? 0) > 0;
  const priceMissing = (costSummary?.price_missing_count ?? 0) > 0;

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-[#ffffff] text-stone-600 flex flex-col py-6 border-r border-stone-200 z-50">
      {/* Brand Logo and Title */}
      <div className="px-6 mb-8">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-[#ff4d00] flex items-center justify-center text-white shadow-none">
            <span className="material-symbols-outlined text-[22px] font-bold">bolt</span>
          </div>
          <div>
            <h1 className="text-stone-950 font-bold text-[17px] tracking-tight leading-tight uppercase font-sans">
              AI Test Case Gen
            </h1>
            <p className="text-[9px] text-[#ff4d00] uppercase tracking-[0.2em] font-bold mt-0.5">
              Enterprise Edition
            </p>
          </div>
        </div>
      </div>

      {/* Main Sidebar Navigation Menu */}
      <nav className="flex-grow px-3 space-y-1 overflow-y-auto custom-scrollbar">
        <div className="space-y-1">
          <button
            onClick={() => setActiveSidebarTab("dashboard")}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-none text-[13px] font-semibold transition-all cursor-pointer ${
              activeSidebarTab === "dashboard"
                ? "bg-[#ff4d00]/5 text-[#ff4d00] border-l-2 border-[#ff4d00]"
                : "hover:bg-stone-50 hover:text-stone-950 text-stone-600"
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">dashboard</span>
            <span className="uppercase tracking-wider text-xs">Dashboard</span>
          </button>
        </div>

        {/* Configurations Box */}
        <hr className="border-stone-200 my-6 mx-3" />
        
        <div className="px-4 pb-4 space-y-4">
          <h2 className="text-[10px] font-semibold text-stone-400 uppercase tracking-[0.25em] leading-none mb-2">
            Settings
          </h2>

          <div className="space-y-1.5">
            <label className="block text-[10px] text-stone-500 uppercase tracking-widest font-bold opacity-85">
              API Key
            </label>
            <div className="relative">
              <input
                type={showApiKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => onApiKeyChange(e.target.value)}
                placeholder="Enter API Key"
                className="w-full bg-stone-50 text-stone-900 border border-stone-200 rounded-none px-3 py-2 text-xs focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all pr-8 font-mono"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-700"
              >
                <span className="material-symbols-outlined text-[15px] select-none">
                  {showApiKey ? "visibility" : "visibility_off"}
                </span>
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="block text-[10px] text-stone-500 uppercase tracking-widest font-bold opacity-85">
              Domain
            </label>
            <input
              type="text"
              value={domain}
              onChange={(e) => onDomainChange(e.target.value)}
              placeholder="e.g. healthcare.auth"
              className="w-full bg-stone-50 text-stone-900 border border-stone-200 rounded-none px-3 py-2 text-xs focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-[10px] text-stone-500 uppercase tracking-widest font-bold opacity-85">
              AI Model
            </label>
            <div className="relative">
              <select
                value={aiModel}
                onChange={(e) => onAiModelChange(e.target.value)}
                className="w-full bg-stone-50 text-stone-900 border border-stone-200 rounded-none px-3 py-2 text-xs focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all appearance-none cursor-pointer pr-8 font-serif italic"
              >
                <option value="Gemini 1.5 Pro" className="bg-[#ffffff] text-stone-900">Gemini 1.5 Pro</option>
                <option value="GPT-4o Enterprise" className="bg-[#ffffff] text-stone-900">GPT-4o Enterprise</option>
                <option value="GPT-4-Turbo" className="bg-[#ffffff] text-stone-900">GPT-4-Turbo</option>
                <option value="Claude 3.5 Sonnet" className="bg-[#ffffff] text-stone-900">Claude 3.5 Sonnet</option>
                <option value="Llama 3 70B" className="bg-[#ffffff] text-stone-900">Llama 3 70B</option>
              </select>
              <span className="material-symbols-outlined absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none text-[16px]">
                expand_more
              </span>
            </div>
          </div>
        </div>

        <hr className="border-stone-200 my-2 mx-3" />

        <div className="px-4 pb-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-[10px] font-semibold text-stone-400 uppercase tracking-[0.25em] leading-none">
              Usage
            </h2>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={onRefreshCosts}
                className="w-7 h-7 flex items-center justify-center border border-stone-200 text-stone-500 hover:text-[#ff4d00] hover:border-[#ff4d00] bg-white cursor-pointer transition-colors"
                title="Refresh usage cost"
              >
                <span className="material-symbols-outlined text-[14px]">refresh</span>
              </button>
              <button
                type="button"
                onClick={onEndCostRun}
                className="w-7 h-7 flex items-center justify-center border border-stone-200 text-stone-500 hover:text-[#ff4d00] hover:border-[#ff4d00] bg-white cursor-pointer transition-colors"
                title="End current cost run"
              >
                <span className="material-symbols-outlined text-[14px]">done_all</span>
              </button>
            </div>
          </div>

          <div className="space-y-2 font-mono">
            <div className="flex items-center justify-between text-[10.5px]">
              <span className="text-stone-500 uppercase tracking-wider">Crawl Data</span>
              <span className="text-stone-900 font-bold">
                {hasCostEvents ? formatUsd(costSummary?.apify_actual_usd) : "--"}
              </span>
            </div>
            <div className="flex items-center justify-between text-[10.5px]">
              <span className="text-stone-500 uppercase tracking-wider">Gen LLM</span>
              <span className="text-stone-900 font-bold">
                {hasCostEvents && !priceMissing ? formatUsd(costSummary?.openai_estimated_usd) : "--"}
              </span>
            </div>
            <div className="flex items-center justify-between border-t border-stone-200 pt-2 text-[11px]">
              <span className="text-stone-800 uppercase tracking-wider font-bold">Total Run</span>
              <span className="text-[#ff4d00] font-bold">
                {hasCostEvents ? formatUsd(costSummary?.total_usd) : "--"}
              </span>
            </div>
          </div>

          <div className="text-[9px] font-mono uppercase tracking-wider text-stone-400 leading-relaxed">
            Events: {costSummary?.event_count ?? 0} | Run: {shortRunId(costSummary?.run_id)}
            {costSummary?.closed ? " | Closed" : ""}
          </div>

          {priceMissing && (
            <div className="flex items-start gap-1.5 text-[9.5px] font-mono uppercase tracking-wider text-amber-700 bg-amber-50 border border-amber-200 px-2 py-2">
              <span className="material-symbols-outlined text-[13px] shrink-0">warning</span>
              <span>OpenAI price config missing</span>
            </div>
          )}
        </div>
      </nav>

      {/* Footer Navigation Section */}
      <div className="mt-auto px-4 space-y-1 border-t border-stone-200 pt-4">
        <button
          onClick={(e) => {
            e.preventDefault();
            onComingSoonClick?.();
          }}
          className="w-full flex items-center gap-3 px-4 py-2 rounded-none text-[12px] text-stone-500 hover:bg-stone-50 hover:text-stone-950 transition-all cursor-pointer bg-transparent border-0 text-left outline-none"
        >
          <span className="material-symbols-outlined text-[18px]">help</span>
          <span className="uppercase tracking-wider text-[11px]">Documentation</span>
        </button>
        <button
          onClick={(e) => {
            e.preventDefault();
            onComingSoonClick?.();
          }}
          className="w-full flex items-center gap-3 px-4 py-2 rounded-none text-[12px] text-stone-500 hover:bg-stone-50 hover:text-stone-950 transition-all cursor-pointer bg-transparent border-0 text-left outline-none"
        >
          <span className="material-symbols-outlined text-[18px]">support_agent</span>
          <span className="uppercase tracking-wider text-[11px]">Support</span>
        </button>
      </div>
    </aside>
  );
}
