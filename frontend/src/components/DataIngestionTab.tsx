import React, { useState, useRef } from "react";
import { IngestStats } from "../types";

interface StagedFile {
  file: File;
  sourceType: string;
}

interface DataIngestionTabProps {
  onDiscover: (text: string, ruleText?: string) => Promise<void>;
  onIngest: (
    files: { file: File; sourceType: string }[],
    prdFile: File | null,
  ) => Promise<IngestStats>;
  ruleText: string;
  onOpenRuleModal: () => void;
}

const SOURCE_OPTIONS = ["survey", "social", "text"];

export default function DataIngestionTab({ onDiscover, onIngest, ruleText, onOpenRuleModal }: DataIngestionTabProps) {
  const [logsText, setLogsText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [prdFile, setPrdFile] = useState<File | null>(null);
  const [stats, setStats] = useState<IngestStats | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const prdInputRef = useRef<HTMLInputElement>(null);

  const inferSourceType = (name: string): string => {
    const lower = name.toLowerCase();
    if (lower.endsWith(".md") || lower.endsWith(".txt")) return "text";
    return "survey";
  };

  const addFiles = (files: FileList) => {
    const next: StagedFile[] = Array.from(files).map((file) => ({
      file,
      sourceType: inferSourceType(file.name),
    }));
    setStagedFiles((prev) => [...prev, ...next]);
    setStats(null);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) addFiles(e.dataTransfer.files);
  };
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) addFiles(e.target.files);
    e.target.value = "";
  };

  const setRowType = (idx: number, type: string) => {
    setStagedFiles((prev) => prev.map((f, i) => (i === idx ? { ...f, sourceType: type } : f)));
  };
  const removeRow = (idx: number) => {
    setStagedFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handlePrdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setPrdFile(e.target.files[0]);
      setStats(null);
    }
    e.target.value = "";
  };

  const handleSubmit = async () => {
    const hasFiles = stagedFiles.length > 0 || prdFile;
    if (!hasFiles && logsText.trim().length === 0) {
      alert("Add at least one file/PRD or paste raw text first.");
      return;
    }
    setLoading(true);
    try {
      // Server-side ingest (FormData) for files + PRD; paste-text goes straight to discover.
      if (hasFiles) {
        const ingestStats = await onIngest(stagedFiles, prdFile);
        setStats(ingestStats);
        // logsText (paste) takes precedence; else "" → backend uses ingested state.
        await onDiscover(logsText.trim(), ruleText);
      } else {
        await onDiscover(logsText, ruleText);
      }
    } catch (e: any) {
      console.error(e);
      alert(e.message || "Ingest/discovery failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto space-y-6">
      {/* Generation rule banner */}
      <div className="flex justify-between items-center bg-white border border-stone-200 px-6 py-4 rounded-none shadow-sm">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[#ff4d00]/80 text-[18px]">settings_suggest</span>
          <span className="text-[10px] font-mono tracking-widest uppercase font-bold text-stone-500">
            Active parsing directives: {ruleText.slice(0, 75)}...
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

      <div className="bg-white border border-stone-200 overflow-hidden flex flex-col h-[calc(100vh-340px)] rounded-none shadow-sm">
        <div className="flex-grow flex flex-col p-8 gap-6 overflow-y-auto">
          <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".csv,.xlsx,.json,.jsonl,.md,.txt" multiple className="hidden" />
          <input type="file" ref={prdInputRef} onChange={handlePrdChange} accept=".md,.txt" className="hidden" />

          {/* Multi-file drop zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`flex flex-col items-center justify-center border-2 border-dashed rounded-none p-8 transition-all cursor-pointer group ${
              isDragging ? "border-[#ff4d00] bg-[#ff4d00]/5" : "border-stone-200 bg-stone-50/50 hover:border-[#ff4d00] hover:bg-stone-50"
            }`}
          >
            <span className={`material-symbols-outlined text-[40px] mb-2 transition-colors ${isDragging ? "text-[#ff4d00]" : "text-stone-400 group-hover:text-[#ff4d00]"}`}>cloud_upload</span>
            <p className="text-[13px] uppercase tracking-wider font-bold text-stone-700 text-center">+ Add files (multi-source)</p>
            <p className="text-[11px] text-stone-400 font-serif italic mt-1 text-center">Supported: .csv, .xlsx, .json, .md, .txt</p>
          </div>

          {/* Staged file list with per-file source dropdown */}
          {stagedFiles.length > 0 && (
            <div className="border border-stone-200">
              {stagedFiles.map((sf, idx) => (
                <div key={idx} className="flex items-center justify-between px-4 py-2.5 border-b border-stone-100 last:border-b-0">
                  <span className="text-[12px] font-mono text-stone-700 truncate flex-1">{sf.file.name}</span>
                  <div className="flex items-center gap-3 shrink-0">
                    <select
                      value={sf.sourceType}
                      onChange={(e) => setRowType(idx, e.target.value)}
                      className="text-[11px] font-mono uppercase tracking-wider border border-stone-300 bg-white px-2 py-1 outline-none focus:border-[#ff4d00] cursor-pointer"
                    >
                      {SOURCE_OPTIONS.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                    <button onClick={() => removeRow(idx)} className="text-stone-400 hover:text-[#ff4d00] bg-transparent border-0 cursor-pointer" title="Remove">
                      <span className="material-symbols-outlined text-[18px]">close</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* PRD context upload */}
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em]">PRD context:</span>
            <button
              type="button"
              onClick={() => prdInputRef.current?.click()}
              className="px-4 py-2 bg-white border border-stone-300 hover:border-[#ff4d00] hover:text-[#ff4d00] font-mono text-[10.5px] uppercase font-bold tracking-widest cursor-pointer"
            >
              Upload PRD
            </button>
            {prdFile && (
              <span className="text-[11px] font-mono text-stone-600">
                {prdFile.name} (loaded)
                <button onClick={() => setPrdFile(null)} className="ml-2 text-[#ff4d00] hover:underline bg-transparent border-0 cursor-pointer uppercase text-[10px] font-bold">clear</button>
              </span>
            )}
          </div>

          {/* Paste raw text */}
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em]">Or paste raw social text (post + comment)</label>
            <textarea
              value={logsText}
              onChange={(e) => setLogsText(e.target.value)}
              className="w-full h-32 bg-stone-50/50 border border-stone-200 rounded-none p-4 text-[13px] font-mono focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all placeholder:text-stone-400 text-stone-800"
              placeholder={`Dán post + comment social ở đây, ví dụ:\n"sạc ở đâu vậy mn ơi"\n"đặt lái thử vf8 t7 đc k"`}
            />
          </div>

          {/* Ingest preview stats */}
          {stats && (
            <div className="border border-stone-200 bg-stone-50/60 px-4 py-3">
              <p className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em] mb-1.5">Ingest preview</p>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] font-mono text-stone-700">
                {stats.sources.map((s, i) => (
                  <span key={i} className={s.status === "skipped" ? "text-rose-600" : ""}>
                    {s.source_type} {s.filename}: {s.rows_in}{s.status === "skipped" ? " skip" : ""}
                  </span>
                ))}
                {stats.prd_loaded && <span className="text-[#ff4d00]">PRD loaded</span>}
                <span>· {stats.total_chars} chars</span>
              </div>
            </div>
          )}

          {/* Run button */}
          <div className="mt-auto flex justify-center pb-2">
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="flex items-center justify-center gap-3 px-10 py-4 bg-[#ff4d00] text-white rounded-none font-bold text-[11px] uppercase tracking-[0.2em] hover:opacity-95 active:scale-95 transition-all disabled:opacity-50 cursor-pointer w-full md:w-auto border-0"
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined animate-spin text-[18px]">sync</span>
                  Ingesting & Discovering Intents...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[18px]">search_check</span>
                  Run Intent Discovery
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
