import React, { useState, useRef } from "react";

interface DataIngestionTabProps {
  onDiscover: (text: string, ruleText?: string) => Promise<void>;
  ruleText: string;
  onOpenRuleModal: () => void;
}

export default function DataIngestionTab({ onDiscover, ruleText, onOpenRuleModal }: DataIngestionTabProps) {
  const [logsText, setLogsText] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFile(files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  const processFile = (file: File) => {
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setLogsText(text);
    };
    reader.readAsText(file);
  };

  const handleSubmit = async () => {
    if (logsText.trim().length === 0) {
      alert("Please upload a file or paste customer support transcripts first.");
      return;
    }
    setLoading(true);
    try {
      await onDiscover(logsText, ruleText);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto space-y-6">
      
      {/* Intent Generation Rule configuration separate box */}
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
        <div className="flex-grow flex flex-col p-8 gap-8 overflow-y-auto">
          
          {/* Hidden File Input for major log ingestion */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".csv,.xlsx,.json,.txt"
          className="hidden"
        />

        {/* Drag & Drop Area for major log ingestion */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={triggerFileSelect}
          className={`flex flex-col items-center justify-center border-2 border-dashed rounded-none p-12 transition-all cursor-pointer group ${
            isDragging
              ? "border-[#ff4d00] bg-[#ff4d00]/5"
              : "border-stone-200 bg-stone-50/50 hover:border-[#ff4d00] hover:bg-stone-50"
          }`}
        >
          <span className={`material-symbols-outlined text-[48px] mb-4 transition-colors ${
            isDragging ? "text-[#ff4d00]" : "text-stone-400 group-hover:text-[#ff4d00]"
          }`}>
            cloud_upload
          </span>
          <p className="text-[14px] uppercase tracking-wider font-bold text-stone-700 text-center">
            {fileName ? `Loaded: ${fileName}` : "Drag and drop CSV/JSON log files here or click to browse"}
          </p>
          <p className="text-[11px] text-stone-400 font-serif italic mt-2 text-center">
            Supported formats: .csv, .xlsx, .json, .txt (max 25MB)
          </p>
          {fileName && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setFileName(null);
                setLogsText("");
              }}
              className="mt-3 text-xs font-bold text-[#ff4d00] hover:underline uppercase tracking-widest bg-transparent border-0 cursor-pointer"
            >
              Clear file
            </button>
          )}
        </div>

        {/* Paste Raw Text Input */}
        <div className="flex flex-col gap-3">
          <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em]">
            Or paste raw customer logs & utterances
          </label>
          <textarea
            value={logsText}
            onChange={(e) => setLogsText(e.target.value)}
            className="w-full h-48 bg-stone-50/50 border border-stone-200 rounded-none p-4 text-[13px] font-mono focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all placeholder:text-stone-400 text-stone-800"
            placeholder={`Paste your customer chat transcripts, logs, or utterances here... For example:
"I got password reset errors"
"Can I transfer my billing account to another username?"
"Where is my invoice for last Monday's backup process?"`}
          />
        </div>

        {/* Compile / Discovery Button */}
        <div className="mt-auto flex justify-center pb-2">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center justify-center gap-3 px-10 py-4 bg-[#ff4d00] text-white rounded-none font-bold text-[11px] uppercase tracking-[0.2em] hover:opacity-95 active:scale-95 transition-all disabled:opacity-50 cursor-pointer w-full md:w-auto border-0"
          >
            {loading ? (
              <>
                <span className="material-symbols-outlined animate-spin text-[18px]">sync</span>
                Synthesizing Logs & Discovering Intents...
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
