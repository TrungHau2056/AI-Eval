import React, { useState, useEffect } from "react";
import { Intent, Persona } from "../types";
import AutoTextarea from "./AutoTextarea";
import { downloadPersonasJson, downloadPersonasCsv } from "../utils/exportPersonas";

interface PersonaPlaygroundTabProps {
  intents: Intent[];
  personas: Persona[];
  onUpdatePersona: (id: string, updated: Partial<Persona>) => void;
  onRegeneratePersona: (id: string, feedback?: string) => Promise<void>;
  onConfirmPersonas: () => void;
  ruleText: string;
  onOpenRuleModal: () => void;
}

export default function PersonaPlaygroundTab({
  intents,
  personas,
  onUpdatePersona,
  onRegeneratePersona,
  onConfirmPersonas,
  ruleText,
  onOpenRuleModal
}: PersonaPlaygroundTabProps) {
  const [loadingMap, setLoadingMap] = useState<{ [id: string]: boolean }>({});
  const [compiling, setCompiling] = useState(false);
  const [feedbackMap, setFeedbackMap] = useState<{ [id: string]: string }>({});
  const [showFeedbackMap, setShowFeedbackMap] = useState<{ [id: string]: boolean }>({});

  const activeIntents = intents.filter((i) => i.selected);
  const displayIntents = activeIntents.length > 0 ? activeIntents : intents;

  const [selectedIntentId, setSelectedIntentId] = useState<string>(() => {
    return displayIntents[0]?.id || "";
  });

  useEffect(() => {
    if (displayIntents.length > 0 && !displayIntents.some(i => i.id === selectedIntentId)) {
      setSelectedIntentId(displayIntents[0].id);
    }
  }, [displayIntents, selectedIntentId]);

  const selectedIntent = displayIntents.find((i) => i.id === selectedIntentId);

  const handleRegen = async (id: string, feedback?: string) => {
    setLoadingMap((prev) => ({ ...prev, [id]: true }));
    setShowFeedbackMap((prev) => ({ ...prev, [id]: false }));
    try {
      await onRegeneratePersona(id, feedback);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingMap((prev) => ({ ...prev, [id]: false }));
    }
  };

  const handleConfirm = async () => {
    setCompiling(true);
    try {
      await onConfirmPersonas();
    } catch (e) {
      console.error(e);
    } finally {
      setCompiling(false);
    }
  };

  // Filter personas for the selected intent
  const selectedIntentObj = displayIntents.find((i) => i.id === selectedIntentId);
  let filteredPersonas = personas.filter((p) => p.intentId === selectedIntentId);

  // Fallback: match by intent name embedded in persona name (e.g. "Happy-path - Find charger")
  if (filteredPersonas.length === 0 && selectedIntentObj) {
    filteredPersonas = personas.filter((p) => p.name.includes(selectedIntentObj.name));
  }

  // Final fallback: show first 2 personas
  if (filteredPersonas.length === 0 && personas.length > 0) {
    filteredPersonas = personas.slice(0, 2);
  }

  const personaA = filteredPersonas.find((p) => p.type === "happy") || filteredPersonas[0];
  const personaB = filteredPersonas.find((p) => p.type === "edge") || filteredPersonas[1] || filteredPersonas[0];

  const renderPersonaCard = (persona: Persona, label: string, isHappy: boolean) => {
    if (!persona) return null;
    const borderColor = isHappy ? "border-t-[#ff4d00]" : "border-t-stone-400";
    const btnBorder = isHappy ? "border-[#ff4d00] text-[#ff4d00] hover:bg-[#ff4d00]/5" : "border-stone-400 text-stone-600 hover:bg-stone-50";
    const icon = isHappy ? "sentiment_satisfied" : "sentiment_very_dissatisfied";
    const iconColor = isHappy ? "text-[#ff4d00]" : "text-stone-500";
    const badge = isHappy ? (
      <span className="px-2 py-0.5 bg-[#ff4d00]/10 text-[#ff4d00] border border-[#ff4d00]/20 text-[9px] font-bold rounded-none uppercase tracking-widest">High Priority</span>
    ) : (
      <span className="px-2 py-0.5 bg-stone-100 text-stone-600 border border-stone-200 text-[9px] font-bold rounded-none uppercase tracking-widest">Boundary Test</span>
    );

    const showFeedback = showFeedbackMap[persona.id] || false;
    const feedback = feedbackMap[persona.id] || "";

    return (
      <div className={`bg-white border border-stone-200 border-t-4 ${borderColor} rounded-none shadow-sm flex flex-col overflow-hidden transition-all`}>
        {/* Header */}
        <div className="p-4 border-b border-stone-200 bg-stone-50/80 flex justify-between items-center select-none">
          <div className="flex items-center gap-2">
            <span className={`material-symbols-outlined ${iconColor} text-[20px]`} style={{ fontVariationSettings: "'FILL' 1" }}>
              {icon}
            </span>
            <h3 className="text-[12px] uppercase tracking-wider font-bold text-stone-900">{label}</h3>
          </div>
          {badge}
        </div>

        {/* Inputs Body */}
        <div className="p-6 space-y-4 flex-grow">
          <div className="grid grid-cols-3 gap-4 items-center">
            <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold">Name</label>
            <input
              type="text"
              value={persona.name}
              onChange={(e) => onUpdatePersona(persona.id, { name: e.target.value })}
              className="col-span-2 bg-stone-50 border border-stone-200 rounded-none px-3 py-1.5 text-[13px] text-stone-900 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all font-sans"
            />
          </div>

          <div className="grid grid-cols-3 gap-4 items-start">
            <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold pt-1">Trigger</label>
            <AutoTextarea
              value={persona.trigger}
              onChange={(e) => onUpdatePersona(persona.id, { trigger: e.target.value })}
              minRows={2}
              className="col-span-2 bg-stone-50 border border-stone-200 rounded-none px-3 py-1.5 text-[13px] text-stone-900 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all resize-none overflow-hidden"
            />
          </div>

          <div className="grid grid-cols-3 gap-4 items-start">
            <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold pt-1">Utterance</label>
            <AutoTextarea
              value={persona.utterance}
              onChange={(e) => onUpdatePersona(persona.id, { utterance: e.target.value })}
              minRows={3}
              className="col-span-2 bg-stone-50 border border-stone-200 rounded-none px-3 py-1.5 text-[13px] text-stone-900 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all placeholder:text-stone-400 font-serif italic resize-none overflow-hidden"
            />
          </div>

          <div className="grid grid-cols-3 gap-4 items-start">
            <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold pt-1">Frequency</label>
            <AutoTextarea
              value={persona.frequencyText || ""}
              onChange={(e) => onUpdatePersona(persona.id, { frequencyText: e.target.value })}
              minRows={2}
              className="col-span-2 bg-stone-50 border border-stone-200 rounded-none px-3 py-1.5 text-[13px] text-stone-900 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all resize-none overflow-hidden"
            />
          </div>

          <div className="grid grid-cols-3 gap-4 items-start">
            <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold pt-1">Pain</label>
            <AutoTextarea
              value={persona.pain}
              onChange={(e) => onUpdatePersona(persona.id, { pain: e.target.value })}
              minRows={2}
              className="col-span-2 bg-stone-50 border border-stone-200 rounded-none px-3 py-1.5 text-[13px] text-stone-900 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all resize-none overflow-hidden"
            />
          </div>

          <div className="grid grid-cols-3 gap-4 items-start">
            <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold pt-1">Reject</label>
            <AutoTextarea
              value={persona.reject}
              onChange={(e) => onUpdatePersona(persona.id, { reject: e.target.value })}
              minRows={2}
              className="col-span-2 bg-stone-50 border border-stone-200 rounded-none px-3 py-1.5 text-[13px] text-stone-900 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all resize-none overflow-hidden"
            />
          </div>

          <div className="grid grid-cols-3 gap-4 items-start">
            <label className="text-[10px] text-stone-500 uppercase tracking-wider font-bold pt-1">Expected AI behavior</label>
            <AutoTextarea
              value={persona.expectedAIBehavior || ""}
              onChange={(e) => onUpdatePersona(persona.id, { expectedAIBehavior: e.target.value })}
              placeholder={isHappy ? "e.g. Acknowledge query and guide user back on happy path." : "e.g. Maintain safety boundaries and output specific rejection code."}
              minRows={2}
              className="col-span-2 bg-stone-50 border border-stone-200 rounded-none px-3 py-1.5 text-[13px] text-stone-900 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all resize-none overflow-hidden"
            />
          </div>
        </div>

        {/* Actions Footer */}
        <div className="p-3 bg-stone-50 border-t border-stone-200">
          {showFeedback && (
            <div className="mb-3 space-y-2">
              <AutoTextarea
                value={feedback}
                onChange={(e) => setFeedbackMap((prev) => ({ ...prev, [persona.id]: e.target.value }))}
                placeholder="Describe what you want to change about this persona..."
                minRows={2}
                className="w-full bg-white border border-stone-300 rounded-none px-3 py-2 text-[12px] text-stone-800 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none resize-none overflow-hidden placeholder:text-stone-400"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowFeedbackMap((prev) => ({ ...prev, [persona.id]: false }))}
                  className="px-3 py-1.5 border border-stone-300 text-stone-600 bg-white rounded-none font-bold text-[10px] uppercase tracking-wider hover:bg-stone-50 transition-all cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => handleRegen(persona.id, feedback || undefined)}
                  disabled={loadingMap[persona.id]}
                  className={`flex items-center gap-1.5 px-3 py-1.5 bg-[#ff4d00] text-white rounded-none font-bold text-[10px] uppercase tracking-wider hover:bg-[#e04400] transition-all cursor-pointer disabled:opacity-50`}
                >
                  {loadingMap[persona.id] ? (
                    <>
                      <span className="material-symbols-outlined text-[14px] animate-spin">sync</span>
                      Regenerating...
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[14px]">play_arrow</span>
                      Submit &amp; Regenerate
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
          {!showFeedback && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setShowFeedbackMap((prev) => ({ ...prev, [persona.id]: true }))}
                disabled={loadingMap[persona.id]}
                className={`flex items-center gap-2 px-4 py-2 border bg-white rounded-none font-bold text-[11px] uppercase tracking-wider transition-all cursor-pointer disabled:opacity-50 ${btnBorder}`}
              >
                {loadingMap[persona.id] ? (
                  <>
                    <span className="material-symbols-outlined text-[16px] animate-spin">sync</span>
                    Regenerating...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[16px]">refresh</span>
                    Regenerate
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">

      {/* Synchronized Generation Rule Banner action */}
      <div className="flex justify-between items-center bg-white border border-stone-200 px-6 py-4 rounded-none shadow-sm">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[#ff4d00]/80 text-[18px]">settings_suggest</span>
          <span className="text-[10px] font-mono tracking-widest uppercase font-bold text-stone-500">
            Active testcase rules: {ruleText.slice(0, 75)}...
          </span>
        </div>
        <button
          type="button"
          onClick={onOpenRuleModal}
          className="flex items-center justify-center gap-2 px-5 py-2.5 bg-white border border-stone-300 hover:border-[#ff4d00] hover:text-[#ff4d00] font-mono text-[10.5px] uppercase font-bold tracking-widest transition-all cursor-pointer shadow-xs shrink-0"
        >
          <span className="material-symbols-outlined text-[16px]">tune</span>
          Configure Rules
        </button>
      </div>

      {/* Intent Selector Dropdown */}
      <div className="bg-white border border-stone-200 p-6 rounded-none shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 select-none">
        <div className="space-y-1">
          <label className="text-[10px] font-bold text-[#ff4d00] uppercase tracking-widest leading-none font-mono flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[15px]">psychology</span>
            Configure Personas per User Intent
          </label>
          <h4 className="text-[15px] font-light text-stone-950 font-serif tracking-tight">
            Select an active intent to inspect and refine its simulated persona pair:
          </h4>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={() => downloadPersonasJson(personas)}
            disabled={personas.length === 0}
            className="flex items-center gap-2 px-4 py-2.5 text-stone-700 bg-white border border-stone-300 rounded-none font-bold text-[11px] uppercase tracking-wider hover:bg-stone-50 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">data_object</span>
            Export JSON
          </button>
          <button
            type="button"
            onClick={() => downloadPersonasCsv(personas, intents)}
            disabled={personas.length === 0}
            className="flex items-center gap-2 px-4 py-2.5 text-stone-700 bg-white border border-stone-300 rounded-none font-bold text-[11px] uppercase tracking-wider hover:bg-stone-50 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">download</span>
            Export CSV
          </button>
          <select
            value={selectedIntentId}
            onChange={(e) => setSelectedIntentId(e.target.value)}
            className="bg-stone-50 border border-stone-300 rounded-none px-4 py-2.5 text-[12.5px] font-semibold text-stone-800 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none tracking-wider custom-scrollbar cursor-pointer"
          >
            {displayIntents.map((intent) => (
              <option key={intent.id} value={intent.id}>
                [{intent.phase}] {intent.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Persona Cards Grid */}
      {filteredPersonas.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {renderPersonaCard(personaA, "Persona A (Happy-path)", true)}
          {renderPersonaCard(personaB, "Persona B (Edge-case)", false)}
        </div>
      ) : (
        <div className="bg-white border border-stone-200 rounded-none shadow-sm p-12 text-center text-stone-400 font-serif italic">
          No personas generated yet for this intent. Generate personas first.
        </div>
      )}

      {/* Confirmation Bottom Panel */}
      <div className="flex flex-col items-center pt-4 select-none">
        <button
          onClick={handleConfirm}
          disabled={compiling}
          className="w-full md:w-auto min-w-[420px] py-4 px-8 bg-[#ff4d00] hover:bg-[#ff4d00]/90 text-white rounded-none font-bold text-[11px] uppercase tracking-[0.2em] hover:opacity-95 active:scale-95 transition-all flex items-center justify-center gap-3 shadow-xl cursor-pointer disabled:opacity-60"
        >
          {compiling ? (
            <>
              <span className="material-symbols-outlined animate-spin text-[20px]">sync</span>
              Compiling Intents &amp; Generating Optimized Cases...
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-[20px]">auto_fix_high</span>
              Confirm Personas &amp; Generate Test Cases
            </>
          )}
        </button>
        <p className="mt-3.5 text-[10px] font-bold text-stone-500 uppercase tracking-widest font-mono flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[14px]">info</span>
          {personas.length} persona{personas.length !== 1 ? "s" : ""} across {displayIntents.length} intent{displayIntents.length !== 1 ? "s" : ""} &bull; Select and refine before compiling.
        </p>
      </div>

    </div>
  );
}
