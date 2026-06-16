import React, { useState } from 'react';
import { TestCasePrompt, Intent, Persona } from '../types';
import * as api from '../api/client';
import GuidelinePanel from './GuidelinePanel';
import { GUIDELINE_KEYS, SINGLE_TURN_GUIDELINE } from '../lib/guidelines';

interface Props {
  prompts: TestCasePrompt[];
  setPrompts: (p: TestCasePrompt[]) => void;
  intents: Intent[];
  personas: Persona[];
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  apiKey: string;
  aiModel: string;
}

export default function SingleTurnTab({ prompts, setPrompts, intents, personas, showToast, apiKey, aiModel }: Props) {
  const [guidance, setGuidance] = useState('');
  const [loading, setLoading] = useState(false);

  const visible = prompts.filter((p) => p.status !== 'deleted');
  const personaCount = personas.filter((p) => p.status !== 'deleted').length;

  const intentLabel = (id: string) => {
    const intent = intents.find((i) => i.id === id);
    return intent ? (intent.goal || intent.context || '').slice(0, 60) : id.slice(0, 8);
  };

  const personaInfo = (id: string) => {
    const persona = personas.find((p) => p.id === id);
    return persona ? { name: persona.name, trait: persona.trait_type } : { name: id.slice(0, 8), trait: 'easy' as const };
  };

  const handleGenerate = async () => {
    if (!apiKey) { showToast('Cần nhập API key.', 'error'); return; }
    setLoading(true);
    try {
      const result = await api.regeneratePrompts(aiModel, apiKey, guidance);
      setPrompts(result);
      showToast(`Đã sinh ${result.length} test case!`, 'success');
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const traitStyle = (trait: string) =>
    trait === 'hard'
      ? 'bg-stone-100 text-stone-600 border-stone-300'
      : 'bg-[#ff4d00]/10 text-[#ff4d00] border-[#ff4d00]/30';

  return (
    <div className="max-w-[1400px] mx-auto space-y-6">
      {/* Controls card */}
      <div className="bg-white border border-black/10 p-6 shadow-sm">
        <h2 className="text-[13px] font-bold text-stone-800 uppercase tracking-[0.2em]">
          5 · Single-turn Test Case
        </h2>
        <p className="text-[12px] text-stone-500 mt-1 font-serif italic">
          Ghép Intent × Persona → test case có goal đo được. Đang có {personaCount} persona.
        </p>

        <div className="flex flex-wrap items-end gap-4 mt-5">
          <div className="flex flex-col gap-1.5 flex-grow min-w-[200px]">
            <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold">Hướng dẫn thêm (tuỳ chọn)</label>
            <input
              type="text"
              value={guidance}
              onChange={(e) => setGuidance(e.target.value)}
              placeholder="VD: viết prompt ngắn, ngôi thứ nhất, tối đa 2 câu"
              className="bg-stone-50 border border-black/10 px-3 py-2 text-[13px] focus:ring-1 focus:ring-[#ff4d00] outline-none text-stone-900"
            />
          </div>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-[#ff4d00] text-white font-bold text-[11px] uppercase tracking-wider hover:opacity-95 transition-all disabled:opacity-40 cursor-pointer"
          >
            <span className={`material-symbols-outlined text-[16px] ${loading ? 'animate-spin' : ''}`}>
              {loading ? 'sync' : 'fact_check'}
            </span>
            {loading ? 'Đang sinh...' : 'Sinh / Tạo lại Test Case'}
          </button>
        </div>

        <div className="mt-5">
          <GuidelinePanel title="Guideline — Tạo Single-turn Test Case" storageKey={GUIDELINE_KEYS.singleTurn} defaultContent={SINGLE_TURN_GUIDELINE} />
        </div>
      </div>

      {/* Table */}
      {visible.length > 0 && (
        <div className="bg-white border border-black/10 shadow-sm overflow-hidden">
          <div className="overflow-auto custom-scrollbar">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 bg-stone-100 z-10">
                <tr className="border-b border-black/10 text-stone-500 font-bold text-[10px] uppercase tracking-wider">
                  <th className="px-4 py-3 w-8 text-center font-mono">#</th>
                  <th className="px-4 py-3 w-[150px]">Persona</th>
                  <th className="px-4 py-3 w-[240px]">Intent (Goal)</th>
                  <th className="px-4 py-3">Start question</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/5 text-stone-700">
                {visible.map((p, idx) => {
                  const info = personaInfo(p.persona_id);
                  return (
                    <tr key={p.id} className="hover:bg-stone-50/50">
                      <td className="px-4 py-3 text-center text-[10px] font-mono text-stone-400">{idx + 1}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider border ${traitStyle(info.trait)}`}>
                          {info.name}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[12px] text-stone-600">{intentLabel(p.intent_id)}</td>
                      <td className="px-4 py-3 text-[13px] text-stone-700 italic font-serif">{p.prompt_text}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="px-6 py-3 border-t border-black/10 bg-stone-50">
            <span className="text-[12px] text-stone-500 font-serif italic">{visible.length} test case</span>
          </div>
        </div>
      )}
    </div>
  );
}
