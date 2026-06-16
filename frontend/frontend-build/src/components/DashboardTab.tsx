import React from 'react';
import { Intent, SubIntent, Persona, TestCasePrompt } from '../types';
import * as api from '../api/client';

interface DashboardTabProps {
  intents: Intent[];
  subIntents: SubIntent[];
  personas: Persona[];
  prompts: TestCasePrompt[];
}

export default function DashboardTab({ intents, subIntents, personas, prompts }: DashboardTabProps) {
  const activeIntents = intents.filter((i) => i.status !== 'deleted');
  const activeSubs = subIntents.filter((s) => s.status !== 'deleted');
  const activePersonas = personas.filter((p) => p.status !== 'deleted');
  const activePrompts = prompts.filter((p) => p.status !== 'deleted');

  const stats: [string, number, string][] = [
    ['Intent', activeIntents.length, 'target'],
    ['Sub-intent', activeSubs.length, 'account_tree'],
    ['Persona', activePersonas.length, 'groups'],
    ['Test Prompt', activePrompts.length, 'fact_check'],
  ];

  // Tỷ lệ "đã chốt" (approved) theo từng loại
  const approvalRates: [string, number, number][] = [
    ['Intent', activeIntents.filter((i) => i.status === 'approved').length, activeIntents.length],
    ['Sub-intent', activeSubs.filter((s) => s.status === 'approved').length, activeSubs.length],
    ['Persona', activePersonas.filter((p) => p.status === 'approved').length, activePersonas.length],
    ['Test Prompt', activePrompts.filter((p) => p.status === 'approved').length, activePrompts.length],
  ];

  const exports: [string, string, string, () => string, boolean][] = [
    ['csv', 'Test Case (CSV)', 'table', api.exportCsv, activePrompts.length > 0],
    ['markdown', 'Báo cáo tổng hợp (Markdown)', 'article', api.exportMarkdown, activePrompts.length > 0],
  ];

  return (
    <div className="max-w-[1400px] mx-auto space-y-6">
      {/* Section header */}
      <div>
        <h2 className="text-[13px] font-bold text-stone-800 uppercase tracking-[0.2em]">Dashboard</h2>
        <p className="text-[12px] text-stone-500 mt-1 font-serif italic">
          Tổng quan pipeline và xuất kết quả.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map(([label, value, icon]) => (
          <div key={label} className="bg-white border border-black/10 p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="material-symbols-outlined text-[#ff4d00] text-[20px]">{icon}</span>
              <span className="text-[28px] font-light text-stone-950 font-serif">{value}</span>
            </div>
            <p className="text-[10px] font-bold text-stone-500 uppercase tracking-widest mt-2 font-mono">{label}</p>
          </div>
        ))}
      </div>

      {/* Approval rates */}
      <div className="bg-white border border-black/10 p-6 shadow-sm">
        <h3 className="text-[12px] font-bold text-stone-700 uppercase tracking-wider mb-4">
          Tỷ lệ đã chốt theo từng loại
        </h3>
        <div className="space-y-3">
          {approvalRates.map(([label, met, total]) => {
            const pct = total ? Math.round((met * 100) / total) : 0;
            return (
              <div key={label} className="flex items-center gap-4">
                <span className="text-[12px] font-mono font-bold text-stone-700 w-28 shrink-0">{label}</span>
                <div className="flex-grow bg-stone-100 h-3 overflow-hidden">
                  <div className="h-full bg-[#ff4d00] transition-all" style={{ width: `${pct}%` }}></div>
                </div>
                <span className="text-[12px] font-mono text-stone-600 w-24 text-right">
                  {met}/{total} ({pct}%)
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Export */}
      <div className="bg-white border border-black/10 p-6 shadow-sm">
        <h3 className="text-[12px] font-bold text-stone-700 uppercase tracking-wider mb-4">Export</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {exports.map(([kind, label, icon, urlFn, enabled]) => (
            <a
              key={kind}
              href={enabled ? urlFn() : undefined}
              download
              className={`flex items-center gap-2 px-4 py-2.5 border font-bold text-[11px] uppercase tracking-wider transition-all ${
                enabled
                  ? 'border-black/10 text-stone-700 hover:bg-stone-50 cursor-pointer'
                  : 'border-black/5 text-stone-300 cursor-not-allowed pointer-events-none'
              }`}
            >
              <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">{icon}</span>
              {label}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
