import React, { useState, useMemo } from "react";
import { Intent } from "../types";
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
}

export default function IntentCurationTab({
  intents,
  onUpdateIntent,
  onToggleSelectAll,
  onAddIntent,
  onProcessIntents,
  ruleText,
  onOpenRuleModal
}: IntentCurationTabProps) {
  const [coverageFilter, setCoverageFilter] = useState<string>("all");

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

  // Một dòng hiển thị: có thể gộp từ nhiều intent gốc (cặp Confirmed PRD+Data).
  // Mỗi field editable route về đúng id intent gốc để sửa không bị lệch bản.
  type DisplayRow = {
    key: string;
    memberIds: string[];
    name: string;
    utterance: string;
    triggerMoment: string;
    phase: string;
    sourceLabel: string; // "prd" | "data" | "PRD+Data"
    coverage: string;
    selected: boolean;
    nameId: string;
    utteranceId: string;
    momentId: string;
    phaseId: string;
  };

  const displayRows = useMemo<DisplayRow[]>(() => {
    const byId = new Map(intents.map((i) => [i.id, i]));
    const consumed = new Set<string>();
    const rows: DisplayRow[] = [];

    const passthrough = (it: Intent): DisplayRow => ({
      key: it.id,
      memberIds: [it.id],
      name: it.name,
      utterance: it.utterance,
      triggerMoment: it.triggerMoment,
      phase: it.phase,
      sourceLabel: it.source || "",
      coverage: it.coverage || "",
      selected: it.selected,
      nameId: it.id,
      utteranceId: it.id,
      momentId: it.id,
      phaseId: it.id,
    });

    for (const it of intents) {
      if (consumed.has(it.id)) continue;

      const isConfirmed = (it.coverage || "") === "confirmed" && (it.matchedIds?.length ?? 0) > 0;
      if (!isConfirmed) {
        rows.push(passthrough(it));
        consumed.add(it.id);
        continue;
      }

      // Gom cluster các intent confirmed nối nhau qua matchedIds (BFS transitively).
      const cluster: Intent[] = [];
      const queue = [it.id];
      const seen = new Set<string>([it.id]);
      while (queue.length) {
        const cur = byId.get(queue.shift()!);
        if (!cur) continue;
        cluster.push(cur);
        for (const mid of cur.matchedIds || []) {
          if (!seen.has(mid) && byId.has(mid)) {
            seen.add(mid);
            queue.push(mid);
          }
        }
      }
      cluster.forEach((c) => consumed.add(c.id));

      const prd = cluster.find((c) => c.source === "prd");
      const data = cluster.find((c) => c.source === "data");

      // Không đủ 2 nguồn → coi như dòng đơn (giữ nguồn của nó).
      if (!prd || !data) {
        rows.push(passthrough(it));
        continue;
      }

      // Trộn: name/moment/phase từ PRD, utterance từ Data.
      rows.push({
        key: cluster.map((c) => c.id).join("+"),
        memberIds: cluster.map((c) => c.id),
        name: prd.name || data.name,
        utterance: data.utterance || prd.utterance,
        triggerMoment: prd.triggerMoment || data.triggerMoment,
        phase: prd.phase || data.phase,
        sourceLabel: "PRD+Data",
        coverage: "confirmed",
        selected: cluster.every((c) => c.selected),
        nameId: prd.id,
        utteranceId: data.id,
        momentId: prd.id,
        phaseId: prd.id,
      });
    }
    return rows;
  }, [intents]);

  const visibleRows =
    coverageFilter === "all" ? displayRows : displayRows.filter((r) => r.coverage === coverageFilter);

  const handleDownloadJson = () => {
    if (intents.length === 0) {
      alert("No intents to export. Run Intent Discovery first.");
      return;
    }
    downloadIntentsJson(intents);
  };

  const handleDownloadCsv = () => {
    if (intents.length === 0) {
      alert("No intents to export. Run Intent Discovery first.");
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
        <div className="px-6 py-4 border-b border-stone-200 flex items-center justify-between bg-stone-50/70">
          <div className="flex items-center gap-4">
            <h2 className="text-[13px] font-bold text-stone-800 uppercase tracking-[0.2em]">Curation Queue</h2>
            {hasCoverage && (
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-stone-500 uppercase tracking-wider">Coverage:</span>
                <select
                  value={coverageFilter}
                  onChange={(e) => setCoverageFilter(e.target.value)}
                  className="text-[11px] font-mono uppercase tracking-wider border border-stone-300 bg-white px-2 py-1 outline-none focus:border-[#ff4d00] cursor-pointer"
                >
                  <option value="all">All</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="prd_only">PRD-only</option>
                  <option value="data_only">Data-only</option>
                </select>
              </div>
            )}
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
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100 text-stone-700">
            {visibleRows.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-stone-400 font-serif italic">
                  No matching curated intents found. Try clicking "Run Intent Discovery" on Step 1, or click "New Intent" to add some!
                </td>
              </tr>
            ) : (
              visibleRows.map((row) => (
                <tr
                  key={row.key}
                  className={`group transition-colors ${
                    row.selected ? "bg-[#ff4d00]/[0.03]" : "hover:bg-stone-50/50"
                  }`}
                >
                  <td className="px-6 py-4 text-center">
                    <input
                      type="checkbox"
                      checked={row.selected}
                      onChange={(e) =>
                        row.memberIds.forEach((id) => onUpdateIntent(id, { selected: e.target.checked }))
                      }
                      className="w-4 h-4 rounded-none bg-white border-stone-300 text-[#ff4d00] focus:ring-[#ff4d00]"
                    />
                  </td>

                  {/* Intent Name input cell */}
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={row.name}
                      onChange={(e) => onUpdateIntent(row.nameId, { name: e.target.value })}
                      className="bg-transparent border-none p-0 text-[13px] font-semibold text-stone-900 w-full focus:ring-0 focus:outline-none focus:border-b focus:border-[#ff4d00]"
                    />
                  </td>

                  {/* Source cell (PRD / Data / PRD+Data) */}
                  <td className="px-4 py-2">
                    {row.sourceLabel && (
                      <span className={`text-[9px] font-bold uppercase tracking-wider py-1 px-2 rounded-none whitespace-nowrap ${
                        row.sourceLabel === "PRD+Data"
                          ? "bg-violet-100 text-violet-800 border border-violet-200/50"
                          : row.sourceLabel === "prd"
                          ? "bg-indigo-100 text-indigo-800 border border-indigo-200/50"
                          : "bg-sky-100 text-sky-800 border border-sky-200/50"
                      }`}>
                        {row.sourceLabel}
                      </span>
                    )}
                  </td>

                  {/* Coverage badge cell */}
                  <td className="px-4 py-2">
                    {row.coverage && COVERAGE_BADGES[row.coverage] && (
                      <span className={`text-[9px] font-bold uppercase tracking-wider py-1 px-2 rounded-none whitespace-nowrap ${COVERAGE_BADGES[row.coverage].cls}`}>
                        {COVERAGE_BADGES[row.coverage].label}
                      </span>
                    )}
                  </td>

                  {/* Phase selector dropdown cell */}
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={row.phase}
                      onChange={(e) => onUpdateIntent(row.phaseId, { phase: e.target.value })}
                      className={`text-[9px] font-bold rounded-none py-1 px-2 uppercase w-full bg-transparent border-none outline-none focus:ring-0 focus:border-b focus:border-[#ff4d00] ${getPhaseStyle(
                        row.phase
                      )}`}
                    />
                  </td>

                  {/* Utterance input cell */}
                  <td className="px-4 py-2">
                    <AutoTextarea
                      value={row.utterance}
                      onChange={(e) => onUpdateIntent(row.utteranceId, { utterance: e.target.value })}
                      minRows={2}
                      className="bg-transparent border-none p-0 text-[13px] text-stone-600 italic font-serif w-full focus:ring-0 focus:outline-none focus:border-b focus:border-[#ff4d00] resize-none overflow-hidden"
                    />
                  </td>

                  {/* Trigger Moment input cell */}
                  <td className="px-4 py-2">
                    <AutoTextarea
                      value={row.triggerMoment}
                      onChange={(e) => onUpdateIntent(row.momentId, { triggerMoment: e.target.value })}
                      minRows={2}
                      className="bg-transparent border-none p-0 text-[13px] text-stone-500 w-full focus:ring-0 focus:outline-none focus:border-b focus:border-[#ff4d00] resize-none overflow-hidden"
                    />
                  </td>

                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination / curation info */}
      <div className="px-6 py-3 border-t border-stone-200 flex items-center justify-between bg-stone-50/70">
        <span className="text-[12px] text-stone-500 font-serif italic">
          {displayRows.length} intents{displayRows.length !== intents.length ? ` (${intents.length} gốc)` : ""} discovered &bull; {selectedCount} selected for compilation
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
