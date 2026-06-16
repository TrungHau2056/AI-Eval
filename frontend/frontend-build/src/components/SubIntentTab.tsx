import React, { useState } from 'react';
import { Intent, SubIntent } from '../types';
import GuidelinePanel from './GuidelinePanel';
import { GUIDELINE_KEYS, SUBINTENT_GUIDELINE } from '../lib/guidelines';

interface Props {
  intents: Intent[];
  subIntents: SubIntent[];
  setSubIntents: (s: SubIntent[]) => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  onApproved: () => void;
}

// Mock tab — no backend. Sub-intents are generated/edited entirely in-state.
const MOCK_TEMPLATES = [
  { title: 'Create intent', description: 'how to create a new intent' },
  { title: 'Update intent', description: 'how to update an existing intent' },
  { title: 'Delete intent', description: 'how to delete an intent' },
  { title: 'Archive intent', description: 'how to archive an intent' },
];

export default function SubIntentTab({ intents, subIntents, setSubIntents, showToast, onApproved }: Props) {
  const [generating, setGenerating] = useState(false);

  const activeIntents = intents.filter((i) => i.status !== 'deleted');
  const visible = subIntents.filter((s) => s.status !== 'deleted');

  const updateSubIntent = (id: string, patch: Partial<SubIntent>) => {
    setSubIntents(subIntents.map((s) => s.id === id ? { ...s, ...patch, status: 'edited' as const } : s));
  };

  const deleteSubIntent = (id: string) => {
    setSubIntents(subIntents.map((s) => s.id === id ? { ...s, status: 'deleted' as const } : s));
  };

  const addSubIntent = (intentId: string) => {
    const newItem: SubIntent = {
      id: `sub-custom-${Date.now()}`,
      intent_id: intentId,
      title: 'New sub-intent',
      description: 'how to ...',
      status: 'edited',
    };
    setSubIntents([...subIntents, newItem]);
  };

  // Mock generation: 2–4 sub-intents per active intent (fallback to a fixed set).
  const handleGenerate = () => {
    setGenerating(true);
    showToast('Generating sub-intents...', 'info');
    setTimeout(() => {
      const base = activeIntents.length ? activeIntents : [{ id: 'mock-intent', goal: 'New intent' } as Intent];
      const generated: SubIntent[] = [];
      base.forEach((intent, ii) => {
        const count = 3 + (ii % 2); // 3 or 4
        const intentName = (intent.goal || intent.context || 'intent').toLowerCase();
        for (let k = 0; k < count; k++) {
          const tpl = MOCK_TEMPLATES[k % MOCK_TEMPLATES.length];
          generated.push({
            id: `sub-${intent.id}-${k}-${Date.now()}`,
            intent_id: intent.id,
            title: tpl.title,
            description: `${tpl.description.replace('intent', intentName)}`,
            status: 'generated',
          });
        }
      });
      setSubIntents(generated);
      setGenerating(false);
      showToast(`Generated ${generated.length} sub-intents (mock)!`, 'success');
    }, 600);
  };

  const handleApprove = () => {
    if (visible.length === 0) { showToast('No sub-intents to approve yet.', 'error'); return; }
    setSubIntents(subIntents.map((s) => s.status !== 'deleted' ? { ...s, status: 'approved' as const } : s));
    showToast(`${visible.length} sub-intents approved!`, 'success');
    onApproved();
  };

  return (
    <div className="max-w-[1400px] mx-auto space-y-4">

      {/* Guideline */}
      <GuidelinePanel title="Guideline — Creating Sub-Intents" storageKey={GUIDELINE_KEYS.subintent} defaultContent={SUBINTENT_GUIDELINE} />

      <div className="bg-white border border-black/10 overflow-hidden flex flex-col h-[calc(100vh-360px)] rounded-none">
        {/* Toolbar */}
        <div className="px-6 py-4 border-b border-black/10 flex items-center justify-between bg-stone-50 gap-4 select-none">
          <div>
            <h2 className="text-[13px] font-bold text-stone-900 uppercase tracking-[0.2em]">3 · Generate Sub-intents</h2>
            <p className="text-[11px] text-stone-500 font-serif italic mt-0.5">Each intent is broken down into sub-intents at the same level of abstraction.</p>
          </div>

          <div className="flex items-center gap-2">
            {/* Generate */}
            <button onClick={handleGenerate} disabled={generating}
              className="flex items-center gap-2 px-4 py-2 text-stone-600 border border-black/10 hover:border-black/20 hover:text-stone-900 text-[11px] uppercase tracking-wider font-bold transition-all disabled:opacity-50 cursor-pointer"
            >
              <span className={`material-symbols-outlined text-[16px] ${generating ? 'animate-spin' : ''}`}>{generating ? 'sync' : 'auto_awesome'}</span>
              Regenerate Sub-Intents
            </button>

            {/* Approve */}
            <button onClick={handleApprove} disabled={visible.length === 0}
              className="flex items-center gap-2 px-6 py-2 bg-[#ff4d00] text-white text-[11px] uppercase tracking-wider font-bold hover:opacity-95 transition-all disabled:opacity-40 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">check_circle</span>
              Generate Persona
            </button>
          </div>
        </div>

        {/* Tree: Intent → Sub-intent */}
        <div className="flex-grow overflow-auto custom-scrollbar p-6">
          <h3 className="text-[12px] font-bold text-stone-700 uppercase tracking-wider mb-5">
            Intent → Sub-intent tree
          </h3>

          {activeIntents.length === 0 ? (
            <p className="text-center py-16 text-stone-400 text-xs font-serif italic">
              No intents yet. Go back to Step 2 to select intents first.
            </p>
          ) : (
            <div className="space-y-6">
              {activeIntents.map((it) => {
                const children = visible.filter((s) => s.intent_id === it.id);
                return (
                  <div key={it.id} className="border-l-2 border-[#ff4d00]/40 pl-4">
                    {/* Intent node */}
                    <div className="flex items-baseline gap-2">
                      <span className="material-symbols-outlined text-[#ff4d00] text-[16px] self-center">target</span>
                      <span className="font-bold text-[14px] text-stone-900">{it.goal || it.context || 'Untitled intent'}</span>
                    </div>
                    <div className="ml-6 text-[10px] text-stone-400 uppercase tracking-wider mt-0.5">
                      {it.phase?.trim() ? it.phase : 'phase unknown'} · {children.length} sub-intent{children.length === 1 ? '' : 's'}
                    </div>

                    {/* Sub-intent children */}
                    <div className="ml-6 mt-3 space-y-3">
                      {children.length === 0 ? (
                        <p className="text-[11px] text-stone-400 italic">— no sub-intents generated yet —</p>
                      ) : (
                        children.map((s) => (
                          <div key={s.id} className="group border-l border-black/10 pl-3 py-0.5 relative">
                            <div className="flex items-start gap-1.5">
                              <span className="text-stone-400 text-[13px] leading-6 select-none">↳</span>
                              <div className="flex-grow">
                                <input
                                  type="text"
                                  value={s.title}
                                  onChange={(e) => updateSubIntent(s.id, { title: e.target.value })}
                                  className="bg-transparent border-none p-0 text-[13px] text-stone-700 font-medium w-full focus:ring-0 focus:outline-none focus:border-b focus:border-[#ff4d00]/50"
                                />
                                <div className="flex items-baseline text-stone-500">
                                  <span className="font-serif italic text-[12px] select-none">"</span>
                                  <input
                                    type="text"
                                    value={s.description}
                                    onChange={(e) => updateSubIntent(s.id, { description: e.target.value })}
                                    placeholder="utterance..."
                                    className="bg-transparent border-none p-0 text-[12px] text-stone-500 font-serif italic w-full focus:ring-0 focus:outline-none placeholder-stone-300"
                                  />
                                  <span className="font-serif italic text-[12px] select-none">"</span>
                                </div>
                              </div>
                              <button onClick={() => deleteSubIntent(s.id)}
                                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-rose-50 text-stone-400 hover:text-rose-500 cursor-pointer shrink-0"
                                title="Delete sub-intent"
                              >
                                <span className="material-symbols-outlined text-[16px]">delete</span>
                              </button>
                            </div>
                          </div>
                        ))
                      )}

                      {/* Add sub-intent under this intent */}
                      <button onClick={() => addSubIntent(it.id)}
                        className="flex items-center gap-1 text-[10px] text-[#ff4d00] hover:underline uppercase tracking-wider font-bold cursor-pointer ml-3"
                      >
                        <span className="material-symbols-outlined text-[14px]">add</span>
                        Add sub-intent
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-black/10 flex items-center justify-between bg-stone-50 select-none">
          <span className="text-[12px] text-stone-500 font-serif italic">
            {visible.length} sub-intents · {subIntents.filter((s) => s.status === 'approved').length} approved
          </span>
          <span className="text-[10px] text-stone-400 font-mono uppercase tracking-widest">
            Mock data · click any line to edit
          </span>
        </div>
      </div>
    </div>
  );
}
