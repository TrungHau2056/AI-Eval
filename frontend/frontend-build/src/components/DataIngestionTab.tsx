import React, { useState, useRef } from 'react';
import * as api from '../api/client';
import GuidelinePanel from './GuidelinePanel';
import { GUIDELINE_KEYS, INTENT_GUIDELINE } from '../lib/guidelines';

interface DataIngestionTabProps {
  onSuccess: (step: number) => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  apiKey: string;
  aiModel: string;
}

export default function DataIngestionTab({ onSuccess, showToast, apiKey, aiModel }: DataIngestionTabProps) {
  const [text, setText] = useState('');
  const [fileName, setFileName] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [guidance, setGuidance] = useState('');
  const [mode, setMode] = useState<'text' | 'csv'>('text');
  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);

  const processFile = (file: File) => {
    if (file.name.endsWith('.csv')) {
      setMode('csv');
      setFileName(file.name);
      if (csvInputRef.current) {
        const dt = new DataTransfer();
        dt.items.add(file);
        csvInputRef.current.files = dt.files;
      }
    } else {
      setMode('text');
      setFileName(file.name);
      const reader = new FileReader();
      reader.onload = (e) => setText((e.target?.result as string) ?? '');
      reader.readAsText(file);
    }
  };

  const clearFile = () => {
    setFileName(null);
    setText('');
    setMode('text');
    if (csvInputRef.current) csvInputRef.current.value = '';
  };

  const switchTab = (tab: 'paste' | 'upload') => {
    setActiveTab(tab);
    if (tab === 'paste') {
      // Switching to paste: drop any selected file and use text mode.
      clearFile();
    }
  };

  const handleSubmit = async () => {
    if (!apiKey.trim()) { showToast('Please enter your API key in the sidebar.', 'error'); return; }
    if (activeTab === 'paste' && !text.trim()) { showToast('No data to analyze yet.', 'error'); return; }
    if (activeTab === 'upload' && !fileName) { showToast('No file selected.', 'error'); return; }

    setLoading(true);
    try {
      if (mode === 'text') {
        await api.submitText(text);
      } else if (csvInputRef.current?.files?.[0]) {
        const fd = new FormData();
        fd.append('file', csvInputRef.current.files[0]);
        await api.submitCSV(fd);
      }
      showToast('Data loaded. Extracting intents...', 'info');
      await api.extractIntents(aiModel, apiKey);
      showToast('Intents extracted successfully!', 'success');
      onSuccess(2);
    } catch (e: any) {
      showToast(e.message ?? 'Error while processing data.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto bg-white border border-black/10 flex flex-col shadow-sm">
      <div className="flex flex-col p-8 gap-6">
        {/* Section header */}
        <div>
          <h2 className="text-[13px] font-bold text-stone-800 uppercase tracking-[0.2em]">
            1 · Raw Data Ingestion
          </h2>
          <p className="text-[12px] text-stone-500 mt-1 font-serif italic">
            Paste text or upload a CSV / TXT / JSON file. Remember to remove PII before importing.
          </p>
        </div>

        {/* Hidden inputs */}
        <input ref={fileInputRef} type="file" accept=".csv,.txt,.json" className="hidden"
          onChange={(e) => e.target.files?.[0] && processFile(e.target.files[0])} />
        <input ref={csvInputRef} type="file" accept=".csv" className="hidden" />

        {/* Method tabs */}
        <div className="flex border-b border-black/10">
          <button
            onClick={() => switchTab('paste')}
            className={`flex items-center gap-2 px-5 py-3 text-[11px] font-bold uppercase tracking-[0.15em] transition-all cursor-pointer border-b-2 -mb-px ${
              activeTab === 'paste'
                ? 'border-[#ff4d00] text-[#ff4d00]'
                : 'border-transparent text-stone-400 hover:text-stone-600'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">edit_note</span>
            Paste Text
          </button>
          <button
            onClick={() => switchTab('upload')}
            className={`flex items-center gap-2 px-5 py-3 text-[11px] font-bold uppercase tracking-[0.15em] transition-all cursor-pointer border-b-2 -mb-px ${
              activeTab === 'upload'
                ? 'border-[#ff4d00] text-[#ff4d00]'
                : 'border-transparent text-stone-400 hover:text-stone-600'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">cloud_upload</span>
            Upload File
          </button>
        </div>

        {/* Tab: Paste raw text */}
        {activeTab === 'paste' && (
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-bold text-stone-500 uppercase tracking-[0.2em]">
              Paste user comments / posts / transcripts
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="w-full h-44 bg-stone-50/50 border border-black/10 p-4 text-[13px] font-mono focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none placeholder:text-stone-400 text-stone-800 custom-scrollbar resize-none"
              placeholder={'Example:\n"I want to know how to schedule a group study session"\n"The app throws an error while I\'m taking a quiz"\n"How can I review lectures I\'ve already watched?"'}
            />
          </div>
        )}

        {/* Tab: Upload file */}
        {activeTab === 'upload' && (
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => { e.preventDefault(); setIsDragging(false); const f = e.dataTransfer.files[0]; if (f) processFile(f); }}
            onClick={() => fileInputRef.current?.click()}
            className={`flex flex-col items-center justify-center border-2 border-dashed p-10 transition-all cursor-pointer group ${
              isDragging ? 'border-[#ff4d00] bg-[#ff4d00]/5' : 'border-black/15 bg-stone-50/50 hover:border-[#ff4d00]'
            }`}
          >
            <span className={`material-symbols-outlined text-[42px] mb-3 transition-colors ${isDragging ? 'text-[#ff4d00]' : 'text-stone-400 group-hover:text-[#ff4d00]'}`}>
              cloud_upload
            </span>
            <p className="text-[13px] uppercase tracking-wider font-bold text-stone-700">
              {fileName ? `Selected: ${fileName}` : 'Drag & drop a file here, or click to browse'}
            </p>
            <p className="text-[11px] text-stone-400 font-serif italic mt-1">
              Supports .csv, .txt, .json
            </p>
            {fileName && (
              <button onClick={(e) => { e.stopPropagation(); clearFile(); }}
                className="mt-3 text-xs font-bold text-[#ff4d00] hover:underline uppercase tracking-widest cursor-pointer"
              >
                Remove file
              </button>
            )}
          </div>
        )}

        {/* Guideline */}
        <GuidelinePanel title="Guideline — Creating Intents" storageKey={GUIDELINE_KEYS.intent} defaultContent={INTENT_GUIDELINE} />

        {/* Submit */}
        <div className="flex justify-center pt-2">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center justify-center gap-3 px-10 py-3.5 bg-[#ff4d00] text-white font-bold text-[11px] uppercase tracking-[0.2em] hover:opacity-95 active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            <span className={`material-symbols-outlined text-[18px] ${loading ? 'animate-spin' : ''}`}>
              {loading ? 'sync' : 'search_check'}
            </span>
            {loading ? 'Discovering intents...' : 'Run Intent Discovery'}
          </button>
        </div>
      </div>
    </div>
  );
}
