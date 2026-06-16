import React, { useState, useEffect, useRef } from 'react';
import { renderMarkdown } from '../lib/markdown';

interface RubricModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const DEFAULT_RUBRIC = `# Rubric Đánh Giá Kết Quả Gen

## Tiêu chí 1: Intent Quality (0–3 điểm)
| Mức | Mô tả |
|-----|-------|
| 3 | Intent rõ ràng, context và goal không trùng lặp, có evidence thực tế |
| 2 | Intent đủ dùng nhưng goal còn chung chung |
| 1 | Intent mơ hồ, context và goal khó phân biệt |
| 0 | Intent không có ý nghĩa hoặc thiếu thông tin |

## Tiêu chí 2: Persona Contrast (0–3 điểm)
| Mức | Mô tả |
|-----|-------|
| 3 | Persona easy/hard rõ nét, trái ngược hợp lý, có tên và mô tả cụ thể |
| 2 | Có sự tương phản nhưng còn mờ nhạt |
| 1 | Hai persona gần giống nhau, khó phân biệt |
| 0 | Persona thiếu thực tế, rập khuôn hoặc vô nghĩa |

## Tiêu chí 3: Test Prompt Effectiveness (0–4 điểm)
| Mức | Mô tả |
|-----|-------|
| 4 | Prompt phản ánh đúng persona + intent, ngôi thứ nhất, có khả năng kích hoạt phản hồi rõ ràng |
| 3 | Prompt đủ tốt, phản ánh được persona nhưng chưa cực kỳ sắc nét |
| 2 | Prompt chung chung, có thể fit nhiều persona khác |
| 1 | Prompt mâu thuẫn với persona hoặc intent |
| 0 | Prompt vô nghĩa hoặc không liên quan |

## Tiêu chí 4: Coverage (0–2 điểm)
| Mức | Mô tả |
|-----|-------|
| 2 | Bộ test case bao phủ đủ các trường hợp từ raw data |
| 1 | Thiếu một số intent/persona quan trọng |
| 0 | Coverage thấp, không đại diện cho raw data |

---

## Hướng dẫn sử dụng

1. Chạy pipeline: Data Ingestion → Intent → Persona → Test Prompt
2. Review từng bước, chỉnh sửa trước khi chốt
3. Export CSV/Markdown, sau đó đánh giá bằng rubric này
4. Tổng điểm tối đa: **12 điểm**

> **Lưu ý:** Rubric này có thể chỉnh sửa trực tiếp để phù hợp với từng domain cụ thể.
`;

const STORAGE_KEY = 'ai_eval_rubric_content';

export default function RubricModal({ isOpen, onClose }: RubricModalProps) {
  const [content, setContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [saved, setSaved] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    setContent(stored ?? DEFAULT_RUBRIC);
  }, []);

  useEffect(() => {
    if (isOpen && isEditing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isOpen, isEditing]);

  const handleSave = () => {
    localStorage.setItem(STORAGE_KEY, content);
    setIsEditing(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = () => {
    if (confirm('Reset về rubric mặc định? Nội dung chỉnh sửa sẽ bị mất.')) {
      setContent(DEFAULT_RUBRIC);
      localStorage.removeItem(STORAGE_KEY);
      setIsEditing(false);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'rubric.md';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-4xl max-h-[88vh] mx-4 bg-white border border-black/10 flex flex-col shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-black/10 bg-stone-50 select-none">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[#ff4d00]/10 border border-[#ff4d00]/30 flex items-center justify-center">
              <span className="material-symbols-outlined text-[18px] text-[#ff4d00]">fact_check</span>
            </div>
            <div>
              <h2 className="text-[13px] font-bold text-stone-900 uppercase tracking-widest">Rubric Đánh Giá</h2>
              <p className="text-[10px] text-stone-400 font-mono">rubric.md — tiêu chí đánh giá kết quả gen</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Download */}
            <button
              onClick={handleDownload}
              title="Download rubric.md"
              className="flex items-center gap-1.5 px-3 py-1.5 text-stone-500 border border-black/10 hover:border-black/20 hover:text-stone-900 text-[10px] uppercase tracking-wider font-bold transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[15px]">download</span>
              Export
            </button>

            {/* Reset */}
            <button
              onClick={handleReset}
              title="Reset về mặc định"
              className="flex items-center gap-1.5 px-3 py-1.5 text-stone-500 border border-black/10 hover:border-rose-300 hover:text-rose-500 text-[10px] uppercase tracking-wider font-bold transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[15px]">restart_alt</span>
              Reset
            </button>

            {/* Edit / Save toggle */}
            {isEditing ? (
              <button
                onClick={handleSave}
                className="flex items-center gap-1.5 px-4 py-1.5 bg-[#ff4d00] text-white text-[10px] uppercase tracking-wider font-bold hover:opacity-90 transition-all cursor-pointer"
              >
                <span className="material-symbols-outlined text-[15px]">save</span>
                {saved ? 'Saved!' : 'Lưu'}
              </button>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-1.5 px-4 py-1.5 text-[#ff4d00] border border-[#ff4d00]/50 hover:bg-[#ff4d00]/10 text-[10px] uppercase tracking-wider font-bold transition-all cursor-pointer"
              >
                <span className="material-symbols-outlined text-[15px]">edit</span>
                Chỉnh sửa
              </button>
            )}

            {/* Close */}
            <button
              onClick={onClose}
              className="p-1.5 text-stone-400 hover:text-stone-900 hover:bg-black/5 transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[20px]">close</span>
            </button>
          </div>
        </div>

        {/* Mode indicator strip */}
        {isEditing && (
          <div className="px-6 py-2 bg-[#ff4d00]/10 border-b border-[#ff4d00]/20 flex items-center gap-2">
            <span className="material-symbols-outlined text-[14px] text-[#ff4d00]">edit_note</span>
            <span className="text-[10px] text-[#ff4d00] uppercase tracking-widest font-bold font-mono">
              Đang chỉnh sửa — nhập Markdown, bấm Lưu khi xong
            </span>
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-hidden">
          {isEditing ? (
            <textarea
              ref={textareaRef}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full h-full min-h-[60vh] bg-stone-50 text-stone-800 font-mono text-[12.5px] p-6 resize-none outline-none focus:ring-0 border-none leading-relaxed custom-scrollbar"
              spellCheck={false}
            />
          ) : (
            <div className="overflow-y-auto max-h-[68vh] p-6 custom-scrollbar">
              {renderMarkdown(content)}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-black/10 bg-stone-50 flex items-center justify-between select-none">
          <span className="text-[10px] text-stone-400 font-mono">
            {content.length} ký tự · {content.split('\n').length} dòng
          </span>
          <span className="text-[10px] text-stone-400 font-mono uppercase tracking-widest">
            Lưu trong trình duyệt · không sync với server
          </span>
        </div>
      </div>
    </div>
  );
}
