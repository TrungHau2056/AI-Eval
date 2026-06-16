import React, { useState } from 'react';
import { Intent } from '../types';
import * as api from '../api/client';

interface Props {
  intents: Intent[];
  setIntents: (i: Intent[]) => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  onApproved: () => void;
  apiKey: string;
  aiModel: string;
}

export default function IntentCurationTab({ intents, setIntents, showToast, onApproved, apiKey, aiModel }: Props) {
  const [search, setSearch] = useState('');
  const [regenerating, setRegenerating] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [guidance, setGuidance] = useState('');
  const [showGuidance, setShowGuidance] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const visible = intents.filter((i) => i.status !== 'deleted').filter((i) => {
    const t = search.toLowerCase();
    return (i.context ?? '').toLowerCase().includes(t) || (i.goal ?? '').toLowerCase().includes(t);
  });

  const allSelected = visible.length > 0 && visible.every((i) => selected.has(i.id));

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    setSelected(allSelected ? new Set() : new Set(visible.map((i) => i.id)));
  };

  // Persisted edits (synced to backend).
  const updateIntent = (id: string, patch: Partial<Intent>) => {
    const updated = intents.map((i) => i.id === id ? { ...i, ...patch, status: 'edited' as const } : i);
    setIntents(updated);
    api.updateIntents([{ id, ...patch }]).catch(() => {});
  };

  // UI-only edits (phase / utterance) — not sent to the backend.
  const updateIntentLocal = (id: string, patch: Partial<Intent>) => {
    setIntents(intents.map((i) => i.id === id ? { ...i, ...patch, status: 'edited' as const } : i));
  };

  const deleteIntent = (id: string) => {
    const updated = intents.map((i) => i.id === id ? { ...i, status: 'deleted' as const } : i);
    setIntents(updated);
    setSelected((prev) => { const next = new Set(prev); next.delete(id); return next; });
    api.updateIntents([{ id, status: 'deleted' }]).catch(() => {});
  };

  const addIntent = () => {
    const newIntent: Intent = {
      id: `custom-${Date.now()}`,
      context: 'New trigger moment',
      goal: 'New intent',
      evidence: [],
      phase: '',
      utterance: '',
      status: 'edited',
    };
    setIntents([newIntent, ...intents]);
  };

  const handleRegenerate = async () => {
    if (!apiKey) { showToast('API key is required.', 'error'); return; }
    setRegenerating(true);
    try {
      const result = await api.regenerateIntents(aiModel, apiKey, guidance);
      setIntents(result);
      showToast('Intents regenerated successfully!', 'success');
      setShowGuidance(false);
      setGuidance('');
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setRegenerating(false);
    }
  };

  const handleGenerateSubIntents = async () => {
    if (selected.size === 0) { showToast('Select at least one intent to generate sub-intents.', 'error'); return; }
    setGenerating(true);
    try {
      // Push edits for the selected intents before moving on.
      const patches = intents
        .filter(i => selected.has(i.id) && i.status === 'edited')
        .map(i => ({ id: i.id, context: i.context, goal: i.goal, status: i.status }));
      if (patches.length) await api.updateIntents(patches);
      showToast(`Generating sub-intents for ${selected.size} intent(s)...`, 'info');
      onApproved();
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto bg-white border border-black/10 overflow-hidden flex flex-col h-[calc(100vh-280px)] rounded-none">

      {/* Toolbar */}
      <div className="px-6 py-4 border-b border-black/10 flex items-center justify-between bg-stone-50 gap-4 select-none">
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-[13px] font-bold text-stone-900 uppercase tracking-[0.2em]">2 · Intent Discovery</h2>
            <p className="text-[11px] text-stone-500 font-serif italic mt-0.5">Review, edit and tick the intents you want to generate sub-intents for.</p>
          </div>
          {/* <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-stone-400 text-[18px]">search</span>
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search intents..."
              className="pl-9 pr-4 py-1.5 bg-stone-50 border border-black/10 text-[12px] w-56 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none rounded-none text-stone-900 placeholder-stone-400"
            />
          </div> */}
        </div>

        <div className="flex items-center gap-2">
          {/* Regenerate */}
          <button onClick={() => setShowGuidance(!showGuidance)}
            className="flex items-center gap-2 px-4 py-2 text-stone-600 border border-black/10 hover:border-black/20 hover:text-stone-900 text-[11px] uppercase tracking-wider font-bold transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">refresh</span>
            Regenerate
          </button>

          {/* Add */}
          <button onClick={addIntent}
            className="flex items-center gap-2 px-4 py-2 text-[#ff4d00] border border-[#ff4d00]/50 hover:bg-[#ff4d00]/10 text-[11px] uppercase tracking-wider font-bold transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">add</span>
            Add
          </button>

          {/* Generate sub-intents */}
          <button onClick={handleGenerateSubIntents} disabled={generating || selected.size === 0}
            className="flex items-center gap-2 px-6 py-2 bg-[#ff4d00] text-white text-[11px] uppercase tracking-wider font-bold hover:opacity-95 transition-all disabled:opacity-40 cursor-pointer"
          >
            {generating ? (
              <><span className="material-symbols-outlined animate-spin text-[16px]">sync</span>Generating...</>
            ) : (
              <><span className="material-symbols-outlined text-[16px]">auto_awesome</span>Generate sub-intent</>
            )}
          </button>
        </div>
      </div>

      {/* Guidance row */}
      {showGuidance && (
        <div className="px-6 py-3 border-b border-[#ff4d00]/20 bg-[#ff4d00]/5 flex items-center gap-3">
          <span className="material-symbols-outlined text-[18px] text-[#ff4d00]">tips_and_updates</span>
          <input
            type="text"
            value={guidance}
            onChange={(e) => setGuidance(e.target.value)}
            placeholder="Additional guidance for the AI (e.g. focus on intents related to scheduling study sessions)"
            className="flex-grow bg-stone-50 border border-black/10 text-[12px] px-3 py-2 text-stone-900 outline-none focus:ring-1 focus:ring-[#ff4d00] font-mono placeholder-stone-400"
          />
          <button onClick={handleRegenerate} disabled={regenerating}
            className="px-5 py-2 bg-[#ff4d00] text-white text-[11px] font-bold uppercase tracking-wider hover:opacity-90 transition-all disabled:opacity-50 cursor-pointer flex items-center gap-2"
          >
            {regenerating ? <span className="material-symbols-outlined animate-spin text-[16px]">sync</span> : <span className="material-symbols-outlined text-[16px]">send</span>}
            Run
          </button>
        </div>
      )}

      {/* Table */}
      <div className="flex-grow overflow-auto custom-scrollbar">
        <table className="w-full text-left border-collapse">
          <thead className="sticky top-0 bg-stone-100 z-10">
            <tr className="border-b border-black/10 text-stone-500 font-bold text-[10px] uppercase tracking-wider">
              <th className="px-4 py-3 w-10 text-center">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleSelectAll}
                  className="w-3.5 h-3.5 accent-[#ff4d00] cursor-pointer align-middle"
                />
              </th>
              <th className="px-4 py-3 w-[240px]">Intent Name</th>
              <th className="px-4 py-3 w-32">Phase</th>
              <th className="px-4 py-3">Utterance</th>
              <th className="px-4 py-3 w-[280px]">Trigger Moment</th>
              <th className="px-4 py-3 w-12"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-black/5 text-stone-800">
            {visible.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-16 text-stone-400 text-xs font-serif italic">
                  No intents yet. Go back to Step 1 to run Intent Discovery.
                </td>
              </tr>
            ) : (
              visible.map((item) => (
                <tr key={item.id} className="group hover:bg-stone-50 transition-colors">
                  <td className="px-4 py-3 text-center align-middle">
                    <input
                      type="checkbox"
                      checked={selected.has(item.id)}
                      onChange={() => toggleSelect(item.id)}
                      className="w-3.5 h-3.5 accent-[#ff4d00] cursor-pointer align-middle"
                    />
                  </td>

                  {/* Intent Name */}
                  <td className="px-4 py-2">
                    <textarea
                      value={item.goal ?? ''}
                      onChange={(e) => updateIntent(item.id, { goal: e.target.value })}
                      rows={2}
                      className="bg-transparent border-none p-0 text-[12.5px] text-stone-900 font-bold w-full focus:ring-0 focus:outline-none resize-none leading-relaxed focus:border-b focus:border-[#ff4d00]/50"
                    />
                  </td>

                  {/* Phase */}
                  <td className="px-4 py-2 align-middle">
                    <input
                      type="text"
                      value={item.phase ?? ''}
                      onChange={(e) => updateIntentLocal(item.id, { phase: e.target.value })}
                      placeholder="—"
                      className="bg-transparent border-none p-0 text-[12.5px] text-stone-700 w-full focus:ring-0 focus:outline-none placeholder-stone-300"
                    />
                  </td>

                  {/* Utterance */}
                  <td className="px-4 py-2 align-middle">
                    <textarea
                      value={item.utterance ?? item.evidence?.[0] ?? ''}
                      onChange={(e) => updateIntentLocal(item.id, { utterance: e.target.value })}
                      rows={2}
                      placeholder="—"
                      className="bg-transparent border-none p-0 text-[12.5px] text-stone-600 italic font-serif w-full focus:ring-0 focus:outline-none resize-none leading-relaxed placeholder-stone-300"
                    />
                  </td>

                  {/* Trigger Moment */}
                  <td className="px-4 py-2 align-middle">
                    <textarea
                      value={item.context ?? ''}
                      onChange={(e) => updateIntent(item.id, { context: e.target.value })}
                      rows={2}
                      className="bg-transparent border-none p-0 text-[12.5px] text-stone-900 w-full focus:ring-0 focus:outline-none resize-none leading-relaxed focus:border-b focus:border-[#ff4d00]/50"
                    />
                  </td>

                  <td className="px-4 py-3 text-right align-middle">
                    <button onClick={() => deleteIntent(item.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-rose-50 text-stone-400 hover:text-rose-500 cursor-pointer"
                      title="Delete intent"
                    >
                      <span className="material-symbols-outlined text-[18px]">delete</span>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="px-6 py-3 border-t border-black/10 flex items-center justify-between bg-stone-50 select-none">
        <span className="text-[12px] text-stone-500 font-serif italic">
          {visible.length} intents · {selected.size} selected
        </span>
        <span className="text-[10px] text-stone-400 font-mono uppercase tracking-widest">
          Click a cell to edit inline
        </span>
      </div>
    </div>
  );
}
