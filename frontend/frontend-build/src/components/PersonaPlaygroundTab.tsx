import React, { useState } from 'react';
import { Persona } from '../types';
import * as api from '../api/client';

interface Props {
  personas: Persona[];
  setPersonas: (p: Persona[]) => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  onApproved: () => void;
  apiKey: string;
  aiModel: string;
}

export default function PersonaPlaygroundTab({ personas, setPersonas, showToast, onApproved, apiKey, aiModel }: Props) {
  const [regenerating, setRegenerating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [guidance, setGuidance] = useState('');
  const [showGuidance, setShowGuidance] = useState(false);

  const visible = personas.filter((p) => p.status !== 'deleted');
  const easyPersonas = visible.filter((p) => p.trait_type === 'easy');
  const hardPersonas = visible.filter((p) => p.trait_type === 'hard');

  const updatePersona = (id: string, patch: Partial<Persona>) => {
    const updated = personas.map((p) => p.id === id ? { ...p, ...patch, status: 'edited' as const } : p);
    setPersonas(updated);
    api.updatePersonas([{ id, ...patch }]).catch(() => {});
  };

  const handleRegenerate = async () => {
    if (!apiKey) { showToast('Cần nhập API key.', 'error'); return; }
    setRegenerating(true);
    try {
      const result = await api.regeneratePersonas(aiModel, apiKey, guidance);
      setPersonas(result);
      showToast('Đã regenerate Persona!', 'success');
      setShowGuidance(false);
      setGuidance('');
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setRegenerating(false);
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      const patches = personas.filter(p => p.status === 'edited').map(p => ({
        id: p.id, name: p.name, description: p.description, trait_type: p.trait_type, status: p.status,
      }));
      if (patches.length) await api.updatePersonas(patches);
      await api.approvePersonas();
      const fresh = await api.getPersonas();
      setPersonas(fresh);
      showToast('Persona đã được chốt! Đang gen Test Prompt...', 'success');
      onApproved();
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setApproving(false);
    }
  };

  const PersonaCard = ({ persona }: { persona: Persona }) => (
    <div className={`bg-[#161616] border border-white/15 border-t-4 flex flex-col overflow-hidden ${
      persona.trait_type === 'easy' ? 'border-t-[#ff4d00]' : 'border-t-stone-500'
    }`}>
      {/* Card Header */}
      <div className="p-4 border-b border-white/15 bg-black/20 flex justify-between items-center select-none">
        <div className="flex items-center gap-2">
          <span
            className={`material-symbols-outlined text-[20px] ${persona.trait_type === 'easy' ? 'text-[#ff4d00]' : 'text-stone-400'}`}
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            {persona.trait_type === 'easy' ? 'sentiment_satisfied' : 'sentiment_very_dissatisfied'}
          </span>
          <div>
            <h3 className="text-[12px] uppercase tracking-wider font-bold text-white">
              {persona.trait_type === 'easy' ? 'Easy Persona' : 'Hard Persona'}
            </h3>
            <p className="text-[9px] text-stone-500 font-mono mt-0.5">intent_id: {persona.intent_id.slice(0, 8)}</p>
          </div>
        </div>
        <span className={`px-2 py-0.5 border text-[9px] font-bold uppercase tracking-widest ${
          persona.trait_type === 'easy'
            ? 'bg-[#ff4d00]/20 text-[#ff4d00] border-[#ff4d00]/30'
            : 'bg-white/10 text-stone-300 border-white/15'
        }`}>
          {persona.trait_type === 'easy' ? 'Hợp tác' : 'Khó tính'}
        </span>
      </div>

      {/* Card Body */}
      <div className="p-5 space-y-4 flex-grow">
        <div className="grid grid-cols-3 gap-3 items-center">
          <label className="text-[10px] text-stone-400 uppercase tracking-wider font-bold">Tên</label>
          <input
            type="text"
            value={persona.name}
            onChange={(e) => updatePersona(persona.id, { name: e.target.value })}
            className="col-span-2 bg-black/30 border border-white/10 px-3 py-1.5 text-[13px] text-white focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all font-sans"
          />
        </div>
        <div className="grid grid-cols-3 gap-3 items-start">
          <label className="text-[10px] text-stone-400 uppercase tracking-wider font-bold pt-1">Mô tả</label>
          <textarea
            value={persona.description}
            onChange={(e) => updatePersona(persona.id, { description: e.target.value })}
            rows={4}
            className="col-span-2 bg-black/30 border border-white/10 px-3 py-1.5 text-[12.5px] text-stone-200 min-h-[90px] focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all font-serif italic leading-relaxed resize-none"
          />
        </div>
        <div className="flex items-center gap-2 text-[9px] text-stone-600 font-mono">
          <span className="material-symbols-outlined text-[13px]">key</span>
          ID: {persona.id}
        </div>
      </div>

      <div className={`p-3 border-t border-white/10 flex items-center justify-between ${
        persona.status === 'approved' ? 'bg-emerald-950/20' : 'bg-black/10'
      }`}>
        <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 border ${
          persona.status === 'approved' ? 'text-emerald-400 border-emerald-800 bg-emerald-950/30' :
          persona.status === 'edited' ? 'text-yellow-400 border-yellow-800' :
          'text-stone-500 border-stone-700'
        }`}>{persona.status}</span>
      </div>
    </div>
  );

  return (
    <div className="max-w-[1400px] mx-auto space-y-6">

      {/* Toolbar */}
      <div className="flex items-center justify-between px-1 select-none">
        <h2 className="text-[13px] font-bold text-white uppercase tracking-[0.2em]">
          Persona Playground — {visible.length} personas
        </h2>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowGuidance(!showGuidance)}
            className="flex items-center gap-2 px-4 py-2 text-stone-300 border border-white/15 hover:border-white/30 hover:text-white text-[11px] uppercase tracking-wider font-bold transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">refresh</span>
            Regenerate
          </button>
          <button onClick={handleApprove} disabled={approving || visible.length === 0}
            className="flex items-center gap-2 px-6 py-2 bg-[#ff4d00] text-white text-[11px] uppercase tracking-wider font-bold hover:opacity-95 transition-all disabled:opacity-40 cursor-pointer"
          >
            {approving
              ? <><span className="material-symbols-outlined animate-spin text-[16px]">sync</span>Đang gen Prompt...</>
              : <><span className="material-symbols-outlined text-[16px]">auto_fix_high</span>Chốt Persona → Gen Test Prompt</>
            }
          </button>
        </div>
      </div>

      {/* Guidance */}
      {showGuidance && (
        <div className="flex items-center gap-3 px-4 py-3 border border-[#ff4d00]/20 bg-[#ff4d00]/5">
          <span className="material-symbols-outlined text-[18px] text-[#ff4d00]">tips_and_updates</span>
          <input type="text" value={guidance} onChange={(e) => setGuidance(e.target.value)}
            placeholder="VD: Persona hard nên mang tính tranh luận hơn, hay đặt câu hỏi ngược lại"
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

      {/* Grid */}
      {visible.length === 0 ? (
        <div className="bg-[#161616] border border-white/15 p-16 text-center">
          <span className="material-symbols-outlined text-[48px] text-stone-700 mb-4 block">person_off</span>
          <p className="text-stone-500 text-xs font-serif italic">Chưa có persona. Quay lại bước Intent và bấm "Chốt Intent".</p>
        </div>
      ) : (
        <>
          {/* Pair intents with their personas */}
          {easyPersonas.map((easy) => {
            const hard = hardPersonas.find((h) => h.intent_id === easy.intent_id);
            return (
              <div key={easy.id} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <PersonaCard persona={easy} />
                {hard ? <PersonaCard persona={hard} /> : <div className="border border-dashed border-white/10 flex items-center justify-center text-stone-700 text-xs font-serif italic">Chưa có hard persona cho intent này</div>}
              </div>
            );
          })}
          {/* Orphaned hard personas */}
          {hardPersonas.filter(h => !easyPersonas.find(e => e.intent_id === h.intent_id)).map((hard) => (
            <div key={hard.id} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-dashed border-white/10 flex items-center justify-center text-stone-700 text-xs font-serif italic">—</div>
              <PersonaCard persona={hard} />
            </div>
          ))}
        </>
      )}
    </div>
  );
}
