import React, { useState } from 'react';
import { TestCasePrompt, Intent, Persona } from '../types';
import * as api from '../api/client';

interface Props {
  prompts: TestCasePrompt[];
  setPrompts: (p: TestCasePrompt[]) => void;
  intents: Intent[];
  personas: Persona[];
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  onOpenRubric: () => void;
  apiKey: string;
  aiModel: string;
}

export default function ExportTab({ prompts, setPrompts, intents, personas, showToast, onOpenRubric, apiKey, aiModel }: Props) {
  const [search, setSearch] = useState('');
  const [regenerating, setRegenerating] = useState(false);
  const [guidance, setGuidance] = useState('');
  const [showGuidance, setShowGuidance] = useState(false);

  const visible = prompts.filter((p) => p.status !== 'deleted');

  const getIntentLabel = (id: string) => {
    const intent = intents.find((i) => i.id === id);
    return intent ? intent.goal.slice(0, 50) : id.slice(0, 8);
  };

  const getPersonaLabel = (id: string) => {
    const persona = personas.find((p) => p.id === id);
    return persona ? `${persona.name} (${persona.trait_type})` : id.slice(0, 8);
  };

  const filtered = visible.filter((p) => {
    const t = search.toLowerCase();
    return (
      p.prompt_text.toLowerCase().includes(t) ||
      getIntentLabel(p.intent_id).toLowerCase().includes(t) ||
      getPersonaLabel(p.persona_id).toLowerCase().includes(t)
    );
  });

  const updatePrompt = (id: string, patch: Partial<TestCasePrompt>) => {
    const updated = prompts.map((p) => p.id === id ? { ...p, ...patch, status: 'edited' as const } : p);
    setPrompts(updated);
    api.updatePrompts([{ id, ...patch }]).catch(() => {});
  };

  const handleRegenerate = async () => {
    if (!apiKey) { showToast('Cần nhập API key.', 'error'); return; }
    setRegenerating(true);
    try {
      const result = await api.regeneratePrompts(aiModel, apiKey, guidance);
      setPrompts(result);
      showToast('Đã regenerate Test Prompt!', 'success');
      setShowGuidance(false);
      setGuidance('');
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setRegenerating(false);
    }
  };

  const handleDownloadCSV = async () => {
    try {
      const url = api.exportCsv();
      const link = document.createElement('a');
      link.href = url;
      link.download = 'test_cases.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast('Đang tải CSV...', 'info');
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleDownloadMarkdown = async () => {
    try {
      const url = api.exportMarkdown();
      const link = document.createElement('a');
      link.href = url;
      link.download = 'test_cases.md';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast('Đang tải Markdown...', 'info');
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto space-y-6">
      
      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Test Prompts', value: visible.length, icon: 'description', accent: true },
          { label: 'Personas', value: personas.filter(p => p.status !== 'deleted').length, icon: 'group', accent: false },
          { label: 'Intents', value: intents.filter(i => i.status !== 'deleted').length, icon: 'label', accent: false },
        ].map((stat) => (
          <div key={stat.label} className="bg-[#161616] border border-white/15 p-5 flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold text-stone-400 uppercase tracking-widest mb-1">{stat.label}</p>
              <h4 className={`text-[28px] font-light font-serif tracking-tight ${stat.accent ? 'text-[#ff4d00]' : 'text-white'}`}>
                {stat.value}
              </h4>
            </div>
            <div className={`w-10 h-10 flex items-center justify-center ${stat.accent ? 'bg-[#ff4d00]/10' : 'bg-white/5'}`}>
              <span className={`material-symbols-outlined text-[20px] ${stat.accent ? 'text-[#ff4d00]' : 'text-stone-400'}`}>{stat.icon}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="bg-[#161616] border border-white/15 overflow-hidden flex flex-col h-[calc(100vh-420px)]">
        {/* Toolbar */}
        <div className="px-6 py-4 border-b border-white/15 flex items-center justify-between bg-black/20 select-none">
          <div className="flex items-center gap-4">
            <h2 className="text-[13px] font-bold text-white uppercase tracking-[0.2em]">Test Prompts</h2>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-stone-500 text-[18px]">search</span>
              <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Tìm kiếm..."
                className="pl-9 pr-4 py-1.5 bg-black/40 border border-white/10 text-[12px] w-56 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none text-white placeholder-stone-600"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={() => setShowGuidance(!showGuidance)}
              className="flex items-center gap-2 px-4 py-2 text-stone-300 border border-white/15 hover:border-white/30 hover:text-white text-[11px] uppercase tracking-wider font-bold transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">refresh</span>
              Regenerate
            </button>

            {/* Rubric button */}
            <button onClick={onOpenRubric}
              className="flex items-center gap-2 px-4 py-2 text-[#ff4d00] border border-[#ff4d00]/50 hover:bg-[#ff4d00]/10 text-[11px] uppercase tracking-wider font-bold transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">fact_check</span>
              Xem Rubric
            </button>

            <button onClick={handleDownloadCSV}
              className="flex items-center gap-2 px-4 py-2 text-stone-200 bg-black/30 border border-white/10 hover:bg-black/50 text-[11px] uppercase tracking-wider font-bold transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">download</span>
              CSV
            </button>
            <button onClick={handleDownloadMarkdown}
              className="flex items-center gap-2 px-4 py-2 text-stone-200 bg-black/30 border border-white/10 hover:bg-black/50 text-[11px] uppercase tracking-wider font-bold transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">article</span>
              Markdown
            </button>
          </div>
        </div>

        {/* Guidance */}
        {showGuidance && (
          <div className="flex items-center gap-3 px-6 py-3 border-b border-[#ff4d00]/20 bg-[#ff4d00]/5">
            <span className="material-symbols-outlined text-[18px] text-[#ff4d00]">tips_and_updates</span>
            <input type="text" value={guidance} onChange={(e) => setGuidance(e.target.value)}
              placeholder="VD: Viết prompt ngắn hơn, sử dụng ngôi thứ nhất, không quá 2 câu"
              className="flex-grow bg-black/40 border border-white/10 text-[12px] px-3 py-2 text-white outline-none focus:ring-1 focus:ring-[#ff4d00] font-mono placeholder-stone-600"
            />
            <button onClick={handleRegenerate} disabled={regenerating}
              className="px-5 py-2 bg-[#ff4d00] text-white text-[11px] font-bold uppercase tracking-wider hover:opacity-90 transition-all disabled:opacity-50 cursor-pointer flex items-center gap-2"
            >
              {regenerating ? <span className="material-symbols-outlined animate-spin text-[16px]">sync</span> : <span className="material-symbols-outlined text-[16px]">send</span>}
              Chạy
            </button>
          </div>
        )}

        {/* Table body */}
        <div className="flex-grow overflow-auto custom-scrollbar">
          <table className="w-full text-left border-collapse">
            <thead className="sticky top-0 bg-[#0d0d0d] z-10 select-none">
              <tr className="border-b border-white/15 text-stone-400 font-bold text-[10px] uppercase tracking-wider">
                <th className="px-4 py-3 w-8 text-center font-mono">#</th>
                <th className="px-4 py-3 w-[200px]">Intent (Goal)</th>
                <th className="px-4 py-3 w-[180px]">Persona</th>
                <th className="px-4 py-3">Test Prompt</th>
                <th className="px-4 py-3 w-20 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-16 text-stone-500 text-xs font-serif italic">
                    Chưa có test prompt. Quay lại bước Persona và bấm "Chốt Persona → Gen Test Prompt".
                  </td>
                </tr>
              ) : (
                filtered.map((p, idx) => (
                  <tr key={p.id} className="group hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3 text-center">
                      <span className="text-[10px] font-mono text-stone-600">{idx + 1}</span>
                    </td>
                    <td className="px-4 py-3 text-[11px] text-stone-300">
                      {getIntentLabel(p.intent_id)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 border ${
                        getPersonaLabel(p.persona_id).includes('easy')
                          ? 'text-[#ff4d00] border-[#ff4d00]/30 bg-[#ff4d00]/10'
                          : 'text-stone-300 border-stone-600 bg-stone-800/50'
                      }`}>
                        {getPersonaLabel(p.persona_id)}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <textarea
                        value={p.prompt_text}
                        onChange={(e) => updatePrompt(p.id, { prompt_text: e.target.value })}
                        rows={3}
                        className="bg-transparent border-none p-0 text-[12.5px] text-stone-200 italic font-serif w-full focus:ring-0 focus:outline-none resize-none leading-relaxed"
                      />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 border ${
                        p.status === 'approved' ? 'text-emerald-400 border-emerald-800 bg-emerald-950/30' :
                        p.status === 'edited' ? 'text-yellow-400 border-yellow-800 bg-yellow-950/30' :
                        'text-stone-400 border-stone-700 bg-stone-800/50'
                      }`}>
                        {p.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Rubric CTA Banner */}
      <div className="bg-[#0d0d0d] border border-[#ff4d00]/20 p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h4 className="text-[12px] font-bold tracking-[0.1em] uppercase flex items-center gap-2 text-white">
            <span className="material-symbols-outlined text-[#ff4d00]" style={{ fontVariationSettings: "'FILL' 1" }}>fact_check</span>
            Sẵn sàng đánh giá kết quả?
          </h4>
          <p className="text-[11px] text-stone-400 font-serif italic">
            Dùng Rubric để đánh giá chất lượng Intent, Persona và Test Prompt đã gen ra. Rubric có thể chỉnh sửa để phù hợp với domain.
          </p>
        </div>
        <button onClick={onOpenRubric}
          className="flex items-center gap-2 px-6 py-3 border border-[#ff4d00] text-[#ff4d00] hover:bg-[#ff4d00]/10 text-[11px] font-bold uppercase tracking-wider transition-all cursor-pointer whitespace-nowrap"
        >
          <span className="material-symbols-outlined text-[18px]">open_in_new</span>
          Mở Rubric Đánh Giá
        </button>
      </div>
    </div>
  );
}
