import React, { useState, useRef } from 'react';
import * as api from '../api/client';

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
  const [mode, setMode] = useState<'text' | 'csv'>('text');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);

  const processFile = (file: File) => {
    if (file.name.endsWith('.csv')) {
      setMode('csv');
      setFileName(file.name);
    } else {
      setMode('text');
      setFileName(file.name);
      const reader = new FileReader();
      reader.onload = (e) => setText(e.target?.result as string ?? '');
      reader.readAsText(file);
    }
    // store file in ref for CSV upload
    if (file.name.endsWith('.csv') && csvInputRef.current) {
      const dt = new DataTransfer();
      dt.items.add(file);
      csvInputRef.current.files = dt.files;
    }
  };

  const handleSubmit = async () => {
    if (!apiKey.trim()) { showToast('Vui lòng nhập API key ở sidebar.', 'error'); return; }
    if (mode === 'text' && !text.trim()) { showToast('Chưa có dữ liệu để phân tích.', 'error'); return; }
    if (mode === 'csv' && !fileName) { showToast('Chưa chọn file CSV.', 'error'); return; }

    setLoading(true);
    try {
      if (mode === 'text') {
        await api.submitText(text);
      } else if (csvInputRef.current?.files?.[0]) {
        const fd = new FormData();
        fd.append('file', csvInputRef.current.files[0]);
        await api.submitCSV(fd);
      }
      showToast('Dữ liệu đã được nạp. Đang trích xuất Intent...', 'info');
      await api.extractIntents(aiModel, apiKey);
      showToast('Trích xuất Intent thành công!', 'success');
      onSuccess(2);
    } catch (e: any) {
      showToast(e.message ?? 'Lỗi khi xử lý dữ liệu.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto bg-[#161616] border border-white/15 overflow-hidden flex flex-col h-[calc(100vh-270px)] rounded-none">
      <div className="flex-grow flex flex-col p-8 gap-6 overflow-y-auto custom-scrollbar">

        {/* Hidden inputs */}
        <input ref={fileInputRef} type="file" accept=".csv,.txt,.json" className="hidden"
          onChange={(e) => e.target.files?.[0] && processFile(e.target.files[0])} />
        <input ref={csvInputRef} type="file" accept=".csv" className="hidden" />

        {/* Mode tabs */}
        <div className="flex gap-0 border-b border-white/10 select-none">
          {(['text', 'csv'] as const).map((m) => (
            <button key={m} onClick={() => setMode(m)}
              className={`px-5 py-2.5 text-[11px] font-bold uppercase tracking-widest transition-all cursor-pointer ${
                mode === m
                  ? 'text-[#ff4d00] border-b-2 border-[#ff4d00]'
                  : 'text-stone-500 hover:text-white'
              }`}
            >
              {m === 'text' ? 'Paste Text' : 'Upload CSV'}
            </button>
          ))}
        </div>

        {mode === 'text' ? (
          <div className="flex flex-col gap-3 flex-grow">
            <label className="text-[10px] font-bold text-stone-400 uppercase tracking-[0.2em]">
              Dán raw data / comment / transcript của user
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="flex-grow bg-black/40 border border-white/15 rounded-none p-4 text-[13px] font-mono focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none transition-all placeholder:text-stone-600 text-white min-h-[280px] custom-scrollbar resize-none"
              placeholder={`Dán nội dung vào đây...\n\nVí dụ:\n"Tôi muốn biết cách đặt lịch học theo nhóm"\n"Ứng dụng báo lỗi khi tôi đang làm bài kiểm tra"\n"Làm thế nào để xem lại bài giảng đã học?"`}
            />
          </div>
        ) : (
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => { e.preventDefault(); setIsDragging(false); const f = e.dataTransfer.files[0]; if (f) processFile(f); }}
            onClick={() => fileInputRef.current?.click()}
            className={`flex flex-col items-center justify-center border-2 border-dashed p-16 transition-all cursor-pointer group flex-grow ${
              isDragging ? 'border-[#ff4d00] bg-[#ff4d00]/10' : 'border-white/15 bg-black/30 hover:border-[#ff4d00] hover:bg-black/40'
            }`}
          >
            <span className={`material-symbols-outlined text-[48px] mb-4 transition-colors ${isDragging ? 'text-[#ff4d00]' : 'text-stone-500 group-hover:text-[#ff4d00]'}`}>
              cloud_upload
            </span>
            <p className="text-[14px] uppercase tracking-wider font-bold text-stone-200">
              {fileName ? `Đã chọn: ${fileName}` : 'Kéo thả file CSV hoặc click để chọn'}
            </p>
            <p className="text-[11px] text-stone-500 font-serif italic mt-2">
              Hỗ trợ: .csv — tối đa 25MB
            </p>
            {fileName && (
              <button onClick={(e) => { e.stopPropagation(); setFileName(null); }}
                className="mt-3 text-xs font-bold text-[#ff4d00] hover:underline uppercase tracking-widest cursor-pointer"
              >
                Xóa file
              </button>
            )}
          </div>
        )}

        {/* Submit */}
        <div className="flex justify-center pb-2">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center justify-center gap-3 px-10 py-4 bg-[#ff4d00] text-white rounded-none font-bold text-[11px] uppercase tracking-[0.2em] hover:opacity-95 active:scale-95 transition-all disabled:opacity-50 cursor-pointer w-full md:w-auto"
          >
            {loading ? (
              <>
                <span className="material-symbols-outlined animate-spin text-[18px]">sync</span>
                Đang phân tích và trích xuất Intent...
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[18px]">search_check</span>
                Chạy Intent Discovery
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
