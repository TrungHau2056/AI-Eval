import React, { useState } from "react";
import { Intent, SourcePost } from "../types";
import AutoTextarea from "./AutoTextarea";
import { downloadIntentsCsv, downloadIntentsJson } from "../utils/exportIntents";

interface IntentCurationTabProps {
  intents: Intent[];
  onUpdateIntent: (id: string, updated: Partial<Intent>) => void;
  onToggleSelectAll: (checked: boolean) => void;
  onAddIntent: () => void;
  onProcessIntents: () => void;
  ruleText: string;
  onOpenRuleModal: () => void;
  onToast?: (message: string, type: "success" | "info" | "error") => void;
}

export default function IntentCurationTab({
  intents,
  onUpdateIntent,
  onToggleSelectAll,
  onAddIntent,
  onProcessIntents,
  ruleText,
  onOpenRuleModal,
  onToast,
}: IntentCurationTabProps) {
  const [sourceFilter, setSourceFilter] = useState<'all' | 'prd' | 'data'>("all");
  const [expandedSourceId, setExpandedSourceId] = useState<string | null>(null);

  const COVERAGE_BADGES: Record<string, { label: string; cls: string }> = {
    confirmed: { label: "✅ Confirmed", cls: "bg-emerald-100 text-emerald-800 border border-emerald-200/50" },
    data_only: { label: "⚠️ Data-only", cls: "bg-amber-100 text-amber-800 border border-amber-200/50" },
    prd_only: { label: "◻️ PRD-only", cls: "bg-stone-100 text-stone-600 border border-stone-300/50" },
  };

  const getPhaseStyle = (phase: string) => {
    if (!phase) return "bg-stone-100 text-stone-600 border border-stone-200/50";
    const hash = phase.toLowerCase().split("").reduce((a, c) => a + c.charCodeAt(0), 0);
    const styles = [
      "bg-orange-100 text-orange-800 border border-orange-200/50",
      "bg-blue-100 text-blue-800 border border-blue-200/30",
      "bg-rose-100 text-rose-800 border border-rose-200/30",
      "bg-emerald-100 text-emerald-800 border border-emerald-200/30",
      "bg-fuchsia-100 text-fuchsia-800 border border-fuchsia-200/30",
      "bg-amber-100 text-amber-800 border border-amber-200/30",
      "bg-cyan-100 text-cyan-800 border border-cyan-200/30",
      "bg-violet-100 text-violet-800 border border-violet-200/30",
    ];
    return styles[hash % styles.length];
  };

  const handleToggleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    onToggleSelectAll(e.target.checked);
  };

  const selectedCount = intents.filter((i) => i.selected).length;
  const hasCoverage = intents.some((i) => i.coverage);
  const prdCount = intents.filter((i) => i.source === 'prd' || i.source === 'prd_inferred').length;
  const dataCount = intents.filter((i) => i.source === 'data').length;

  // Lookup by id so PRD intents confirmed against a data intent (via matchedIds) can
  // surface that data intent's source posts even though PRD intents carry none of their own.
  const intentById = React.useMemo(() => {
    const map = new Map<string, Intent>();
    for (const it of intents) map.set(it.id, it);
    return map;
  }, [intents]);

  const getEffectiveSourcePosts = (item: Intent): SourcePost[] => {
    if (item.sourcePosts && item.sourcePosts.length > 0) return item.sourcePosts;
    if (!item.matchedIds || item.matchedIds.length === 0) return [];
    const seen = new Set<string>();
    const posts: SourcePost[] = [];
    for (const mid of item.matchedIds) {
      const matched = intentById.get(mid);
      for (const p of matched?.sourcePosts ?? []) {
        const key = p.url || p.textExcerpt;
        if (!seen.has(key)) {
          seen.add(key);
          posts.push(p);
          if (posts.length >= 3) return posts;
        }
      }
    }
    return posts;
  };

  const sortBySource = (list: Intent[]) =>
    [...list].sort((a, b) => {
      const order = { prd: 0, prd_inferred: 1, data: 2 };
      return (order[a.source as keyof typeof order] ?? 3) - (order[b.source as keyof typeof order] ?? 3);
    });

  const visibleIntents = sortBySource(
    sourceFilter === "all"
      ? intents
      : sourceFilter === "prd"
      ? intents.filter((i) => i.source === 'prd' || i.source === 'prd_inferred')
      : intents.filter((i) => i.source === sourceFilter)
  );

  const handleDownloadJson = () => {
    if (intents.length === 0) {
      onToast?.("No intents to export. Run Intent Discovery first.", "error");
      return;
    }
    downloadIntentsJson(intents);
  };

  const handleDownloadCsv = () => {
    if (intents.length === 0) {
      onToast?.("No intents to export. Run Intent Discovery first.", "error");
      return;
    }
    downloadIntentsCsv(intents);
  };

  return (
    <div className="max-w-[1400px] mx-auto space-y-6">
      
      {/* Synchronized Generation Rule Banner separate box */}
      <div className="flex justify-between items-center bg-white border border-stone-200 px-6 py-4 rounded-none shadow-sm">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[#ff4d00]/80 text-[18px]">settings_suggest</span>
          <span className="text-[10px] font-mono tracking-widest uppercase font-bold text-stone-500">
            Active persona rules: {ruleText.slice(0, 75)}...
          </span>
        </div>
        <button
          type="button"
          onClick={onOpenRuleModal}
          className="flex items-center justify-center gap-2 px-5 py-2.5 bg-white border border-stone-300 hover:border-[#ff4d00] hover:text-[#ff4d00] font-mono text-[10.5px] uppercase font-bold tracking-widest transition-all cursor-pointer shadow-xs shrink-0"
        >
          <span className="material-symbols-outlined text-[16px]">tune</span>
          Configure Generation Rules
        </button>
      </div>

      <div className="bg-white border border-stone-200 overflow-hidden flex flex-col h-[calc(100vh-350px)] rounded-none shadow-sm">
        {/* Table Header / Actions */}
        <div className="border-b border-stone-200">
          {/* Source Tabs */}
          <div className="px-6 pt-4 flex items-center gap-0">
            {(
              [
                { key: 'all', label: 'All', count: intents.length },
                { key: 'prd', label: 'PRD Explicit', count: prdCount },
                { key: 'data', label: 'Data', count: dataCount },
              ] as const
            ).map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setSourceFilter(tab.key)}
                className={`px-4 py-2 mr-1 text-[10px] font-mono font-bold uppercase tracking-widest transition-all border-b-2 whitespace-nowrap cursor-pointer ${
                  sourceFilter === tab.key
                    ? tab.key === 'prd'
                      ? 'border-indigo-500 text-indigo-700'
                      : tab.key === 'data'
                      ? 'border-sky-500 text-sky-700'
                      : 'border-[#ff4d00] text-[#ff4d00]'
                    : 'border-transparent text-stone-400 hover:text-stone-600'
                }`}
              >
                {tab.label}
                {tab.count > 0 && (
                  <span className={`ml-1.5 px-1.5 py-0.5 rounded-none text-[9px] font-bold ${
                    sourceFilter === tab.key
                      ? tab.key === 'prd'
                        ? 'bg-indigo-100 text-indigo-700'
                        : tab.key === 'data'
                        ? 'bg-sky-100 text-sky-700'
                        : 'bg-[#ff4d00]/10 text-[#ff4d00]'
                      : 'bg-stone-100 text-stone-500'
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className="px-6 py-3 flex items-center justify-between bg-stone-50/70">
          <div className="flex items-center gap-4">
            <h2 className="text-[13px] font-bold text-stone-800 uppercase tracking-[0.2em]">Curation Queue</h2>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleDownloadJson}
              disabled={intents.length === 0}
              className="flex items-center gap-2 px-4 py-2 text-stone-700 bg-white border border-stone-200 rounded-none font-bold text-[11px] uppercase tracking-wider hover:bg-stone-50 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">data_object</span>
              Download JSON
            </button>
            <button
              type="button"
              onClick={handleDownloadCsv}
              disabled={intents.length === 0}
              className="flex items-center gap-2 px-4 py-2 text-stone-700 bg-white border border-stone-200 rounded-none font-bold text-[11px] uppercase tracking-wider hover:bg-stone-50 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">download</span>
              Download CSV
            </button>
            <button
              onClick={onAddIntent}
              className="flex items-center gap-2 px-6 py-2 text-[#ff4d00] border border-[#ff4d00] rounded-none font-bold text-[11px] uppercase tracking-wider hover:bg-[#ff4d00]/10 transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px] font-bold">add</span>
              New Intent
            </button>
            <button
              onClick={onProcessIntents}
              disabled={selectedCount === 0}
              className="flex items-center gap-2 px-6 py-2 bg-[#ff4d00] text-white rounded-none font-bold text-[11px] uppercase tracking-wider hover:opacity-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              Process Selected ({selectedCount})
            </button>
          </div>
          </div>
        </div>

        {/* Database Grid */}
      <div className="flex-grow overflow-auto custom-scrollbar">
        <table className="w-full text-left border-collapse">
          <thead className="sticky top-0 bg-stone-105 bg-[#f1f3f5] shadow-xs z-10">
            <tr className="border-b border-stone-200 text-stone-500 font-bold text-[10px] uppercase tracking-wider">
              <th className="px-6 py-3 w-12 text-center">
                <input
                  type="checkbox"
                  onChange={handleToggleSelectAll}
                  checked={intents.length > 0 && intents.every((i) => i.selected)}
                  className="w-4 h-4 rounded-none bg-white border-stone-300 text-[#ff4d00] focus:ring-[#ff4d00]"
                />
              </th>
              <th className="px-4 py-3 w-[230px]">Intent Name</th>
              <th className="px-4 py-3 w-[90px]">Source</th>
              <th className="px-4 py-3 w-[130px]">Coverage</th>
              <th className="px-4 py-3 w-[130px]">Phase</th>
              <th className="px-4 py-3">Utterance (Typical User Ask)</th>
              <th className="px-4 py-3 w-[230px]">Trigger Moment</th>
              <th className="px-4 py-3 w-[80px] text-center">Post</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100 text-stone-700">
            {visibleIntents.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-12 text-stone-400 font-serif italic">
                  No matching curated intents found. Try clicking "Run Intent Discovery" on Step 1, or click "New Intent" to add some!
                </td>
              </tr>
            ) : (
              visibleIntents.map((item) => {
                const effectivePosts = getEffectiveSourcePosts(item);
                return (
                <React.Fragment key={item.id}>
                <tr
                  className={`group transition-colors ${
                    item.selected
                      ? item.source === 'prd_inferred'
                        ? "bg-violet-50/40"
                        : "bg-[#ff4d00]/[0.03]"
                      : item.source === 'prd_inferred'
                      ? "bg-violet-50/20 hover:bg-violet-50/40"
                      : "hover:bg-stone-50/50"
                  }`}
                >
                  <td className="px-6 py-4 text-center">
                    <input
                      type="checkbox"
                      checked={item.selected}
                      onChange={(e) => onUpdateIntent(item.id, { selected: e.target.checked })}
                      className="w-4 h-4 rounded-none bg-white border-stone-300 text-[#ff4d00] focus:ring-[#ff4d00]"
                    />
                  </td>
                  
                  {/* Intent Name input cell */}
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={item.name}
                      onChange={(e) => onUpdateIntent(item.id, { name: e.target.value })}
                      className={`bg-transparent border-none p-0 text-[13px] font-semibold w-full focus:ring-0 focus:outline-none focus:border-b focus:border-[#ff4d00] ${
                        item.source === 'prd_inferred' ? 'text-violet-900 italic' : 'text-stone-900'
                      }`}
                    />
                  </td>

                  {/* Source cell (PRD Explicit / AI Explored / Data) */}
                  <td className="px-4 py-2">
                    {item.source && (
                      <span className={`text-[9px] font-bold uppercase tracking-wider py-1 px-2 rounded-none ${
                        item.source === "prd"
                          ? "bg-indigo-100 text-indigo-800 border border-indigo-200/50"
                          : item.source === "prd_inferred"
                          ? "bg-violet-100 text-violet-800 border border-violet-200/50"
                          : "bg-sky-100 text-sky-800 border border-sky-200/50"
                      }`}>
                        {item.source === "prd" ? "explicit" : item.source === "prd_inferred" ? "inferred" : "data"}
                      </span>
                    )}
                  </td>

                  {/* Coverage badge cell */}
                  <td className="px-4 py-2">
                    {item.coverage && COVERAGE_BADGES[item.coverage] && (
                      <span className={`text-[9px] font-bold uppercase tracking-wider py-1 px-2 rounded-none whitespace-nowrap ${COVERAGE_BADGES[item.coverage].cls}`}>
                        {COVERAGE_BADGES[item.coverage].label}
                      </span>
                    )}
                  </td>

                  {/* Phase selector dropdown cell */}
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={item.phase}
                      onChange={(e) => onUpdateIntent(item.id, { phase: e.target.value })}
                      className={`text-[9px] font-bold rounded-none py-1 px-2 uppercase w-full bg-transparent border-none outline-none focus:ring-0 focus:border-b focus:border-[#ff4d00] ${getPhaseStyle(
                        item.phase
                      )}`}
                    />
                  </td>

                  {/* Utterance input cell */}
                  <td className="px-4 py-2">
                    <AutoTextarea
                      value={item.utterance}
                      onChange={(e) => onUpdateIntent(item.id, { utterance: e.target.value })}
                      minRows={2}
                      className="bg-transparent border-none p-0 text-[13px] text-stone-600 italic font-serif w-full focus:ring-0 focus:outline-none focus:border-b focus:border-[#ff4d00] resize-none overflow-hidden"
                    />
                  </td>

                  {/* Trigger Moment input cell */}
                  <td className="px-4 py-2">
                    <AutoTextarea
                      value={item.triggerMoment}
                      onChange={(e) => onUpdateIntent(item.id, { triggerMoment: e.target.value })}
                      minRows={2}
                      className="bg-transparent border-none p-0 text-[13px] text-stone-500 w-full focus:ring-0 focus:outline-none focus:border-b focus:border-[#ff4d00] resize-none overflow-hidden"
                    />
                  </td>

                  {/* Post cell — opens the source post(s) this intent was derived/confirmed from */}
                  <td className="px-4 py-2 text-center">
                    {effectivePosts.length > 0 && (
                      <button
                        onClick={() => setExpandedSourceId(expandedSourceId === item.id ? null : item.id)}
                        className={`inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide px-2 py-1 rounded-none border transition-colors cursor-pointer ${
                          expandedSourceId === item.id
                            ? "bg-emerald-600 text-white border-emerald-600"
                            : "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                        }`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${expandedSourceId === item.id ? "bg-white" : "bg-emerald-500"}`} />
                        {effectivePosts.length}
                      </button>
                    )}
                  </td>
                </tr>

                {/* Expandable source posts row */}
                {expandedSourceId === item.id && effectivePosts.length > 0 && (
                  <tr key={`${item.id}-sources`} className="bg-emerald-50/40">
                    <td colSpan={8} className="px-8 py-3">
                      <p className="text-[9px] font-bold uppercase tracking-widest text-emerald-700 mb-2">
                        Source Posts ({effectivePosts.length})
                      </p>
                      <div className="space-y-2">
                        {effectivePosts.map((post: SourcePost, idx: number) => (
                          <div key={idx} className="flex items-start gap-3 bg-white border border-emerald-100 rounded-none p-3">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-[9px] font-bold uppercase tracking-wide text-emerald-700 bg-emerald-100 px-1.5 py-0.5">
                                  {post.platform || "social"}
                                </span>
                                {post.username && (
                                  <span className="text-[10px] text-stone-500">@{post.username}</span>
                                )}
                              </div>
                              <p className="text-[11px] text-stone-600 italic leading-relaxed line-clamp-3">
                                "{post.textExcerpt}"
                              </p>
                            </div>
                            {post.url && (
                              <a
                                href={post.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="shrink-0 text-[10px] text-[#ff4d00] hover:underline font-mono mt-0.5"
                              >
                                ↗
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
                </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination / curation info */}
      <div className="px-6 py-3 border-t border-stone-200 flex items-center justify-between bg-stone-50/70">
        <span className="text-[12px] text-stone-500 font-serif italic">
          {intents.length} intents discovered &bull; {selectedCount} selected for compilation
        </span>
        <div className="flex items-center gap-2">
          <button className="p-1 hover:bg-stone-100 rounded-none disabled:opacity-30 text-stone-400 cursor-pointer" disabled>
            <span className="material-symbols-outlined text-[18px]">chevron_left</span>
          </button>
          <span className="text-[11px] font-bold px-2 text-stone-600 font-mono">1 of 1</span>
          <button className="p-1 hover:bg-stone-100 rounded-none disabled:opacity-30 text-stone-400 cursor-pointer" disabled>
            <span className="material-symbols-outlined text-[18px]">chevron_right</span>
          </button>
        </div>
      </div>
    </div>
  </div>
);
}
