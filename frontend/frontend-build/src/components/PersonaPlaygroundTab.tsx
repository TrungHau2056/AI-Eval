import React, { useState, useEffect } from 'react';
import { Persona, Intent, SubIntent } from '../types';
import GuidelinePanel from './GuidelinePanel';
import { GUIDELINE_KEYS, PERSONA_GUIDELINE } from '../lib/guidelines';

interface Props {
  personas: Persona[];
  setPersonas: (p: Persona[]) => void;
  intents: Intent[];
  subIntents: SubIntent[];
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  onApproved: () => void;
  apiKey: string;
  aiModel: string;
}

// Field definitions — label is shown as a normal field title (not the variable name).
// `long` fields render as a textarea; the rest render as a single-line input.
const FIELDS: { key: keyof Persona; label: string; long?: boolean }[] = [
  { key: 'persona_type', label: 'Persona Type' },
  { key: 'user_profile', label: 'User Profile', long: true },
  { key: 'estimated_user_ratio', label: 'Estimated User Ratio' },
  { key: 'usage_frequency', label: 'Usage Frequency' },
  { key: 'reason_to_use', label: 'Reason to Use', long: true },
  { key: 'sample_start_query', label: 'Sample Start Query', long: true },
  { key: 'special_situation', label: 'Special Situation', long: true },
  { key: 'why_this_persona_is_different', label: 'Why This Persona Is Different', long: true },
  { key: 'expected_behavior_or_need', label: 'Expected Behavior or Need', long: true },
  { key: 'not_needed', label: 'Not Needed', long: true },
];

export default function PersonaPlaygroundTab({ personas, setPersonas, intents, subIntents, showToast, onApproved }: Props) {
  const [generating, setGenerating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [intentFilter, setIntentFilter] = useState<string>('all');

  const activeIntents = intents.filter((i) => i.status !== 'deleted');
  const activeSubIntents = subIntents.filter((s) => s.status !== 'deleted');
  const visible = personas
    .filter((p) => p.status !== 'deleted')
    .filter((p) => intentFilter === 'all' || p.intent_id === intentFilter);

  const intentLabel = (id?: string) => {
    if (!id) return 'Unassigned intent';
    const intent = intents.find((i) => i.id === id);
    return intent ? (intent.goal || intent.context || 'Untitled intent') : id.slice(0, 8);
  };

  // Mock: one persona per sub-intent. Tolerant of partial/messy sub-intent data.
  const buildPersonas = (): Persona[] =>
    activeSubIntents.map((sub, idx) => {
      const intentName = intentLabel(sub.intent_id);
      const title = sub.title?.trim() || 'Untitled sub-intent';
      const description = sub.description ?? '';
      const cooperative = idx % 2 === 0;
      return {
        id: `persona-${sub.id}-${Date.now()}`,
        intent_id: sub.intent_id,
        name: `Persona — ${title}`,
        description,
        trait_type: cooperative ? 'easy' : 'hard',
        status: 'generated',
        sub_intent_id: sub.id,
        sub_intent_num: idx + 1,
        sub_intent_name: title,
        persona_num: idx + 1,
        persona_type: cooperative ? 'Cooperative user' : 'Demanding user',
        user_profile: `A user dealing with "${intentName}".`,
        estimated_user_ratio: cooperative ? '60%' : '40%',
        usage_frequency: cooperative ? 'Daily' : 'Occasionally',
        reason_to_use: description,
        sample_start_query: description ? `"${description}"` : '',
        special_situation: cooperative ? 'None' : 'Under time pressure or facing an error',
        why_this_persona_is_different: cooperative
          ? 'Provides clear, complete information up front.'
          : 'Vague, easily frustrated, asks follow-up questions.',
        expected_behavior_or_need: `Wants to ${title.toLowerCase()} quickly and reliably.`,
        not_needed: 'Lengthy explanations or unrelated suggestions.',
      };
    });

  // Auto-generate on first visit if we have sub-intents but no personas yet.
  useEffect(() => {
    try {
      if (personas.filter((p) => p.status !== 'deleted').length === 0 && activeSubIntents.length > 0) {
        setPersonas(buildPersonas());
      }
    } catch (e: any) {
      showToast(e?.message ?? 'Failed to generate personas.', 'error');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const updatePersona = (id: string, patch: Partial<Persona>) => {
    setPersonas(personas.map((p) => p.id === id ? { ...p, ...patch, status: 'edited' as const } : p));
  };

  const deletePersona = (id: string) => {
    setPersonas(personas.map((p) => p.id === id ? { ...p, status: 'deleted' as const } : p));
  };

  const handleGenerate = () => {
    if (activeSubIntents.length === 0) { showToast('No sub-intents to generate personas from.', 'error'); return; }
    setGenerating(true);
    showToast('Generating personas...', 'info');
    setTimeout(() => {
      const built = buildPersonas();
      setPersonas(built);
      setGenerating(false);
      showToast(`Generated ${built.length} personas (one per sub-intent)!`, 'success');
    }, 600);
  };

  const handleApprove = () => {
    if (visible.length === 0) { showToast('No personas to approve yet.', 'error'); return; }
    setApproving(true);
    setPersonas(personas.map((p) => p.status !== 'deleted' ? { ...p, status: 'approved' as const } : p));
    showToast('Personas approved! Generating test prompts...', 'success');
    setApproving(false);
    onApproved();
  };

  const Field = ({ persona, field }: { persona: Persona; field: typeof FIELDS[number] }) => (
    <div className="grid grid-cols-3 gap-3 items-start">
      <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold pt-1.5">{field.label}</label>
      {field.long ? (
        <textarea
          value={(persona[field.key] as string) ?? ''}
          onChange={(e) => updatePersona(persona.id, { [field.key]: e.target.value } as Partial<Persona>)}
          rows={2}
          className="col-span-2 bg-stone-50 border border-black/10 px-3 py-1.5 text-[12.5px] text-stone-700 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all leading-relaxed resize-none"
        />
      ) : (
        <input
          type="text"
          value={(persona[field.key] as string) ?? ''}
          onChange={(e) => updatePersona(persona.id, { [field.key]: e.target.value } as Partial<Persona>)}
          className="col-span-2 bg-stone-50 border border-black/10 px-3 py-1.5 text-[12.5px] text-stone-900 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all"
        />
      )}
    </div>
  );

  const PersonaCard = ({ persona }: { persona: Persona }) => (
    <div className={`bg-white border border-black/10 border-t-4 flex flex-col overflow-hidden ${
      persona.trait_type === 'easy' ? 'border-t-[#ff4d00]' : 'border-t-stone-400'
    }`}>
      {/* Card Header */}
      <div className="p-4 border-b border-black/10 bg-stone-50 flex justify-between items-start gap-3 select-none">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={`material-symbols-outlined text-[20px] shrink-0 ${persona.trait_type === 'easy' ? 'text-[#ff4d00]' : 'text-stone-400'}`}
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            {persona.trait_type === 'easy' ? 'sentiment_satisfied' : 'sentiment_very_dissatisfied'}
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[9px] font-bold uppercase tracking-widest text-stone-400">
                Persona #{persona.persona_num ?? '—'}
              </span>
              <span className="text-[9px] font-bold uppercase tracking-widest text-stone-400">
                · Sub-intent #{persona.sub_intent_num ?? '—'}
              </span>
            </div>
            <input
              type="text"
              value={persona.name}
              onChange={(e) => updatePersona(persona.id, { name: e.target.value })}
              className="bg-transparent border-none p-0 text-[13px] font-bold text-stone-900 w-full focus:ring-0 focus:outline-none focus:border-b focus:border-[#ff4d00]/50"
            />
            <p className="text-[10px] text-stone-500 font-serif italic truncate mt-0.5">
              {persona.sub_intent_name ?? '—'} · {intentLabel(persona.intent_id)}
            </p>
          </div>
        </div>
        <button onClick={() => deletePersona(persona.id)}
          className="p-1 hover:bg-rose-50 text-stone-400 hover:text-rose-500 cursor-pointer shrink-0"
          title="Delete persona"
        >
          <span className="material-symbols-outlined text-[18px]">delete</span>
        </button>
      </div>

      {/* Card Body: labeled fields */}
      <div className="p-5 space-y-3 flex-grow">
        {/* Sub-intent No. / Name (read-only references) */}
        <div className="grid grid-cols-3 gap-3 items-center">
          <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold">Sub-intent No.</label>
          <span className="col-span-2 text-[12.5px] text-stone-700 font-mono">{persona.sub_intent_num ?? '—'}</span>
        </div>
        <div className="grid grid-cols-3 gap-3 items-start">
          <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold pt-1">Sub-intent Name</label>
          <input
            type="text"
            value={persona.sub_intent_name ?? ''}
            onChange={(e) => updatePersona(persona.id, { sub_intent_name: e.target.value })}
            className="col-span-2 bg-stone-50 border border-black/10 px-3 py-1.5 text-[12.5px] text-stone-900 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all"
          />
        </div>
        <div className="grid grid-cols-3 gap-3 items-center">
          <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold">Persona No.</label>
          <span className="col-span-2 text-[12.5px] text-stone-700 font-mono">{persona.persona_num ?? '—'}</span>
        </div>
        <div className="grid grid-cols-3 gap-3 items-start">
          <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold pt-1">Persona Name</label>
          <input
            type="text"
            value={persona.name}
            onChange={(e) => updatePersona(persona.id, { name: e.target.value })}
            className="col-span-2 bg-stone-50 border border-black/10 px-3 py-1.5 text-[12.5px] text-stone-900 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all"
          />
        </div>

        {FIELDS.map((f) => <Field key={f.key as string} persona={persona} field={f} />)}
      </div>

      {/* Card Footer */}
      <div className={`p-3 border-t border-black/10 flex items-center justify-between ${
        persona.status === 'approved' ? 'bg-emerald-50' : 'bg-stone-50'
      }`}>
        <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 border ${
          persona.status === 'approved' ? 'text-emerald-700 border-emerald-200 bg-emerald-50' :
          persona.status === 'edited' ? 'text-amber-700 border-amber-200 bg-amber-50' :
          'text-stone-600 border-stone-300 bg-stone-100'
        }`}>{persona.status}</span>
      </div>
    </div>
  );

  return (
    <div className="max-w-[1400px] mx-auto space-y-4">

      {/* Guideline */}
      <GuidelinePanel title="Guideline — Creating Personas" storageKey={GUIDELINE_KEYS.persona} defaultContent={PERSONA_GUIDELINE} />

      {/* Toolbar */}
      <div className="flex items-center justify-between px-1 gap-4 select-none">
        <h2 className="text-[13px] font-bold text-stone-900 uppercase tracking-[0.2em]">
          Persona Playground — {visible.length} personas
        </h2>
        <div className="flex items-center gap-2">
          {/* Filter by Intent */}
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-stone-400 text-[18px]">filter_list</span>
            <select
              value={intentFilter}
              onChange={(e) => setIntentFilter(e.target.value)}
              className="bg-stone-50 border border-black/10 px-3 py-2 text-[11px] text-stone-900 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none cursor-pointer uppercase tracking-wider font-bold"
            >
              <option value="all">All intents</option>
              {activeIntents.map((i) => (
                <option key={i.id} value={i.id}>{intentLabel(i.id).slice(0, 50)}</option>
              ))}
            </select>
          </div>

          <button onClick={handleGenerate} disabled={generating}
            className="flex items-center gap-2 px-4 py-2 text-stone-600 border border-black/10 hover:border-black/20 hover:text-stone-900 text-[11px] uppercase tracking-wider font-bold transition-all disabled:opacity-50 cursor-pointer"
          >
            <span className={`material-symbols-outlined text-[16px] ${generating ? 'animate-spin' : ''}`}>{generating ? 'sync' : 'auto_awesome'}</span>
            Regenerate
          </button>
          <button onClick={handleApprove} disabled={approving || visible.length === 0}
            className="flex items-center gap-2 px-6 py-2 bg-[#ff4d00] text-white text-[11px] uppercase tracking-wider font-bold hover:opacity-95 transition-all disabled:opacity-40 cursor-pointer"
          >
            {approving
              ? <><span className="material-symbols-outlined animate-spin text-[16px]">sync</span>Generating prompts...</>
              : <><span className="material-symbols-outlined text-[16px]">auto_fix_high</span>Generate Single-turnTestcase</>
            }
          </button>
        </div>
      </div>

      {/* Grid */}
      {visible.length === 0 ? (
        <div className="bg-white border border-black/10 p-16 text-center">
          <span className="material-symbols-outlined text-[48px] text-stone-300 mb-4 block">person_off</span>
          <p className="text-stone-400 text-xs font-serif italic">
            No personas yet. Make sure you have sub-intents, then click "Regenerate".
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
          {visible.map((persona) => <PersonaCard key={persona.id} persona={persona} />)}
        </div>
      )}
    </div>
  );
}
