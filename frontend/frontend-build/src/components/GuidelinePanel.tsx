import React, { useState, useRef, useEffect } from 'react';
import { renderMarkdown } from '../lib/markdown';

interface GuidelinePanelProps {
  title: string;
  storageKey: string;
  defaultContent: string;
}

// Collapsible guideline shown above a "gen" button. Collapsed by default; expanding
// reveals the content plus Edit + Reset. Edit toggles to Save (persists to localStorage).
export default function GuidelinePanel({ title, storageKey, defaultContent }: GuidelinePanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [saved, setSaved] = useState(false);
  const [content, setContent] = useState(defaultContent);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem(storageKey);
    setContent(stored ?? defaultContent);
  }, [storageKey, defaultContent]);

  useEffect(() => {
    if (expanded && isEditing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [expanded, isEditing]);

  const handleSave = () => {
    localStorage.setItem(storageKey, content);
    setIsEditing(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = () => {
    if (confirm('Reset guideline về mặc định? Nội dung chỉnh sửa sẽ bị mất.')) {
      setContent(defaultContent);
      localStorage.removeItem(storageKey);
      setIsEditing(false);
    }
  };

  return (
    <div className="bg-white border border-black/10 overflow-hidden">
      {/* Header bar (always visible) */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3 bg-stone-50 hover:bg-black/5 transition-colors cursor-pointer select-none"
      >
        <div className="flex items-center gap-2.5">
          <span className="material-symbols-outlined text-[18px] text-[#ff4d00]">tips_and_updates</span>
          <span className="text-[11px] font-bold text-stone-700 uppercase tracking-[0.15em]">{title}</span>
        </div>
        <span className="material-symbols-outlined text-[20px] text-stone-400">
          {expanded ? 'expand_less' : 'expand_more'}
        </span>
      </button>

      {/* Body (only when expanded) */}
      {expanded && (
        <div className="border-t border-black/10">
          {/* Edit-mode strip */}
          {isEditing && (
            <div className="px-5 py-2 bg-[#ff4d00]/10 border-b border-[#ff4d00]/20 flex items-center gap-2">
              <span className="material-symbols-outlined text-[14px] text-[#ff4d00]">edit_note</span>
              <span className="text-[10px] text-[#ff4d00] uppercase tracking-widest font-bold font-mono">
                Đang chỉnh sửa — nhập Markdown, bấm Save khi xong
              </span>
            </div>
          )}

          {isEditing ? (
            <textarea
              ref={textareaRef}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full min-h-[280px] bg-stone-50 text-stone-800 font-mono text-[12.5px] p-5 resize-y outline-none focus:ring-0 border-none leading-relaxed custom-scrollbar"
              spellCheck={false}
            />
          ) : (
            <div className="p-5 max-h-[420px] overflow-y-auto custom-scrollbar">
              {renderMarkdown(content)}
            </div>
          )}

          {/* Footer actions */}
          <div className="px-5 py-3 border-t border-black/10 bg-stone-50 flex items-center justify-end gap-2 select-none">
            <button
              onClick={handleReset}
              title="Reset về mặc định"
              className="flex items-center gap-1.5 px-3 py-1.5 text-stone-500 border border-black/10 hover:border-rose-300 hover:text-rose-500 text-[10px] uppercase tracking-wider font-bold transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[15px]">restart_alt</span>
              Reset
            </button>
            {isEditing ? (
              <button
                onClick={handleSave}
                className="flex items-center gap-1.5 px-4 py-1.5 bg-[#ff4d00] text-white text-[10px] uppercase tracking-wider font-bold hover:opacity-90 transition-all cursor-pointer"
              >
                <span className="material-symbols-outlined text-[15px]">save</span>
                {saved ? 'Saved!' : 'Save'}
              </button>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-1.5 px-4 py-1.5 text-[#ff4d00] border border-[#ff4d00]/50 hover:bg-[#ff4d00]/10 text-[10px] uppercase tracking-wider font-bold transition-all cursor-pointer"
              >
                <span className="material-symbols-outlined text-[15px]">edit</span>
                Edit
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
