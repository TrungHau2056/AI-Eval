import React, { useState } from "react";
import { TestCase } from "../types";
import AutoTextarea from "./AutoTextarea";

interface ExportTabProps {
  testCases: TestCase[];
  onUpdateTestCase: (id: string, updated: Partial<TestCase>) => void;
  onRunTest: () => void;
  onOpenLogs: (tc: TestCase) => void;
}

export default function ExportTab({
  testCases,
  onUpdateTestCase,
  onRunTest,
  onOpenLogs
}: ExportTabProps) {
  const [search, setSearch] = useState("");

  const filtered = testCases.filter((tc) => {
    const s = search.toLowerCase();
    return (
      tc.id.toLowerCase().includes(s) ||
      tc.intentName.toLowerCase().includes(s) ||
      tc.personaName.toLowerCase().includes(s) ||
      tc.simulatedPrompt.toLowerCase().includes(s) ||
      tc.expectedOutcome.toLowerCase().includes(s)
    );
  });

  const getStatusStyle = (status?: string) => {
    switch (status) {
      case "passed":
        return "bg-orange-100 text-[#ff4d00] border border-[#ff4d00]/20 rounded-none";
      case "failed":
        return "bg-rose-100 text-rose-700 border border-rose-200 rounded-none";
      case "running":
        return "bg-blue-100 text-blue-700 border border-blue-200 rounded-none animate-pulse";
      case "pending":
      default:
        return "bg-stone-100 text-stone-600 border border-stone-200 rounded-none";
    }
  };

  const handleDownloadCSV = () => {
    const headers = ["Test ID", "Intent Name", "Persona", "Simulated Prompt", "Expected Outcome", "Goal"];
    const rows = testCases.map((tc) => [
      tc.id,
      tc.intentName,
      tc.personaName,
      `"${tc.simulatedPrompt.replace(/"/g, '""')}"`,
      `"${tc.expectedOutcome.replace(/"/g, '""')}"`,
      `"${(tc.goal || "").replace(/"/g, '""')}"`
    ]);
    
    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
      
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "ai_test_suite_export.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
 
  const handleDownloadMarkdown = () => {
    let md = `# AI Generated Test Suite - Enterprise Diagnostics\n\n`;
    md += `| Test ID | Intent Name | Persona Archetype | Simulated User Prompt | Expected Outcome | Goal |\n`;
    md += `|---|---|---|---|---|---|\n`;
    testCases.forEach((tc) => {
      md += `| ${tc.id} | ${tc.intentName} | ${tc.personaName} | \`${tc.simulatedPrompt}\` | ${tc.expectedOutcome} | ${tc.goal || ""} |\n`;
    });

    const blob = new Blob([md], { type: "text/markdown;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "ai_test_suite_export.md");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const completedTests = testCases.filter(t => t.status && t.status !== "pending").length;
  const passedTests = testCases.filter(t => t.status === "passed").length;
  const successPercentage = completedTests > 0 ? Math.round((passedTests / completedTests) * 100) : null;

  return (
    <div className="max-w-[1400px] mx-auto space-y-6">

      {/* Main Table Card Area */}
      <div className="bg-white border border-stone-200 rounded-none shadow-sm overflow-hidden flex flex-col h-[calc(100vh-290px)]">
        {/* Actions bar */}
        <div className="px-6 py-4 border-b border-stone-200 flex items-center justify-between bg-stone-50/70 select-none">
          <div className="flex items-center gap-4">
            <h2 className="text-[13px] font-bold text-stone-800 uppercase tracking-[0.2em]">Finalized Test Suite</h2>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-stone-400 text-[18px]">
                search
              </span>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search compiled cases..."
                className="pl-9 pr-4 py-1.5 bg-white border border-stone-200 text-[12px] w-64 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none rounded-none text-stone-800 placeholder-stone-400"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onRunTest}
              className="flex items-center gap-2 px-4 py-2 text-white bg-[#ff4d00] border border-[#ff4d00] rounded-none font-bold text-[11px] uppercase tracking-wider hover:bg-[#e04400] transition-all cursor-pointer shadow-xs"
            >
              <span className="material-symbols-outlined text-[16px]">play_circle</span>
              Run Test
            </button>
            <button
              type="button"
              onClick={handleDownloadCSV}
              className="flex items-center gap-2 px-4 py-2 text-stone-700 bg-white border border-stone-200 rounded-none font-bold text-[11px] uppercase tracking-wider hover:bg-stone-50 transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">download</span>
              Download CSV (Jira)
            </button>
            <button
              type="button"
              onClick={handleDownloadMarkdown}
              className="flex items-center gap-2 px-4 py-2 text-stone-700 bg-white border border-stone-200 rounded-none font-bold text-[11px] uppercase tracking-wider hover:bg-stone-50 transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px] text-[#ff4d00]">article</span>
              Download Markdown (Docs)
            </button>
          </div>
        </div>

        {/* Compile / Diagnostic Table Grid */}
        <div className="flex-grow overflow-auto custom-scrollbar">
          <table className="w-full text-left border-collapse">
            <thead className="sticky top-0 bg-[#f1f3f5] shadow-xs z-10 select-none">
              <tr className="border-b border-stone-200 text-stone-500 font-bold text-[10px] uppercase tracking-wider">
                <th className="px-6 py-3 w-12 text-center">
                  <input
                    type="checkbox"
                    checked={testCases.length > 0 && testCases.every((t) => t.selected)}
                    onChange={(e) => {
                      const checked = e.target.checked;
                      testCases.forEach((t) => onUpdateTestCase(t.id, { selected: checked }));
                    }}
                    className="w-4 h-4 rounded-none bg-white border-stone-300 text-[#ff4d00] focus:ring-[#ff4d00]"
                  />
                </th>
                <th className="px-4 py-3 w-36">Test ID</th>
                <th className="px-4 py-3 w-[220px]">Intent Name</th>
                <th className="px-4 py-3 w-[200px]">Simulated Persona</th>
                <th className="px-4 py-3">Simulated User Prompt</th>
                <th className="px-4 py-3">Expected Outcome</th>
                <th className="px-4 py-3 w-56">Goal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100 text-stone-700">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-stone-400 font-serif italic">
                    No matching generated test cases found in compile stream.
                  </td>
                </tr>
              ) : (
                filtered.map((tc) => (
                  <tr
                    key={tc.id}
                    onClick={() => {
                      if (tc.status && tc.status !== "pending") {
                        onOpenLogs(tc);
                      }
                    }}
                    className={`transition-colors group ${
                      tc.status && tc.status !== "pending" ? "cursor-pointer hover:bg-stone-50/50" : ""
                    } ${tc.selected ? "bg-[#ff4d00]/[0.03]" : ""}`}
                  >
                    <td className="px-6 py-4 text-center" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={tc.selected}
                        onChange={(e) => onUpdateTestCase(tc.id, { selected: e.target.checked })}
                        className="w-4 h-4 rounded-none bg-white border-stone-300 text-[#ff4d00] focus:ring-[#ff4d00]"
                      />
                    </td>

                    <td className="px-4 py-4 font-mono text-[11px] font-bold text-[#ff4d00]">
                      {tc.id}
                    </td>

                    <td className="px-4 py-4 font-semibold text-[13px] text-stone-950">
                      {tc.intentName}
                    </td>

                    <td className="px-4 py-4 text-stone-500 text-[12px]">
                      {tc.personaName}
                    </td>

                    <td className="px-4 py-2">
                      <AutoTextarea
                        value={tc.simulatedPrompt}
                        readOnly
                        minRows={2}
                        className="w-full bg-transparent border-none p-0 text-[13px] text-stone-600 font-serif italic focus:ring-0 focus:outline-none resize-none overflow-hidden"
                      />
                    </td>

                    <td className="px-4 py-2">
                      <AutoTextarea
                        value={tc.expectedOutcome}
                        readOnly
                        minRows={2}
                        className="w-full bg-transparent border-none p-0 text-[12px] text-stone-500 focus:ring-0 focus:outline-none resize-none overflow-hidden"
                      />
                    </td>

                    <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                      <AutoTextarea
                        value={tc.goal || ""}
                        onChange={(e) => onUpdateTestCase(tc.id, { goal: e.target.value })}
                        placeholder="Assert boundary policy validation"
                        minRows={2}
                        className="w-full bg-stone-50 border border-stone-200 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none text-[11px] px-2.5 py-1 rounded-none text-stone-800 font-mono resize-none overflow-hidden"
                      />
                      {tc.status && tc.status !== "pending" && (
                        <div className="flex items-center gap-1 mt-1 text-[9px] uppercase tracking-wider font-mono justify-between">
                          <span className={`${tc.status === 'passed' ? 'text-green-600' : tc.status === 'failed' ? 'text-rose-600' : 'text-blue-600'}`}>
                            {tc.status}
                          </span>
                          {tc.logs && tc.logs.length > 0 && (
                            <button
                              onClick={() => onOpenLogs(tc)}
                              className="text-[9px] text-[#ff4d00] uppercase font-bold tracking-widest hover:underline bg-transparent border-0 cursor-pointer"
                            >
                              Logs
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
