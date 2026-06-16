import React, { useState, useEffect, useRef } from 'react';

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

  // Very minimal markdown renderer for headings, tables, bold, italic, blockquote
  const renderMarkdown = (md: string) => {
    const lines = md.split('\n');
    const result: React.ReactNode[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // H1
      if (line.startsWith('# ')) {
        result.push(<h1 key={i} className="text-[18px] font-bold text-white mb-4 mt-2 tracking-tight">{line.slice(2)}</h1>);
        i++; continue;
      }
      // H2
      if (line.startsWith('## ')) {
        result.push(<h2 key={i} className="text-[13px] font-bold text-[#ff4d00] uppercase tracking-widest mb-3 mt-6 flex items-center gap-2">
          <span className="w-4 h-[1px] bg-[#ff4d00] inline-block" />
          {line.slice(3)}
        </h2>);
        i++; continue;
      }
      // H3
      if (line.startsWith('### ')) {
        result.push(<h3 key={i} className="text-[12px] font-bold text-stone-300 mb-2 mt-4">{line.slice(4)}</h3>);
        i++; continue;
      }
      // HR
      if (line.startsWith('---')) {
        result.push(<hr key={i} className="border-white/10 my-6" />);
        i++; continue;
      }
      // Blockquote
      if (line.startsWith('> ')) {
        result.push(
          <blockquote key={i} className="border-l-2 border-[#ff4d00]/50 pl-4 py-1 my-2 text-stone-400 text-[12px] font-serif italic bg-[#ff4d00]/5">
            {line.slice(2).replace(/\*\*(.*?)\*\*/g, '$1')}
          </blockquote>
        );
        i++; continue;
      }
      // Table: detect header row
      if (line.startsWith('|') && i + 1 < lines.length && lines[i + 1].startsWith('|---')) {
        const headers = line.split('|').filter((c) => c.trim()).map((c) => c.trim());
        i += 2; // skip separator
        const rows: string[][] = [];
        while (i < lines.length && lines[i].startsWith('|')) {
          rows.push(lines[i].split('|').filter((c) => c.trim()).map((c) => c.trim()));
          i++;
        }
        result.push(
          <div key={`table-${i}`} className="overflow-x-auto my-3">
            <table className="w-full text-left border-collapse text-[12px]">
              <thead>
                <tr className="border-b border-white/15 text-stone-400 text-[10px] uppercase tracking-wider">
                  {headers.map((h, hi) => (
                    <th key={hi} className="py-2 px-3 font-bold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {rows.map((row, ri) => (
                  <tr key={ri} className="hover:bg-white/[0.02] transition-colors">
                    {row.map((cell, ci) => (
                      <td key={ci} className={`py-2 px-3 ${ci === 0 ? 'font-bold text-[#ff4d00] font-mono' : 'text-stone-300'}`}>
                        {cell.replace(/\*\*(.*?)\*\*/g, '$1')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
      // Skip table separator lines
      if (line.startsWith('|---')) { i++; continue; }
      // Ordered / unordered list
      if (/^\d+\.\s/.test(line) || line.startsWith('- ')) {
        const text = line.replace(/^\d+\.\s/, '').replace(/^- /, '');
        result.push(
          <li key={i} className="text-stone-300 text-[12.5px] ml-4 mb-1 list-disc list-inside font-serif">
            {text.replace(/\*\*(.*?)\*\*/g, '$1')}
          </li>
        );
        i++; continue;
      }
      // Empty line
      if (line.trim() === '') {
        result.push(<div key={i} className="h-2" />);
        i++; continue;
      }
      // Paragraph with inline bold/italic
      const rendered = line
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-bold">$1</strong>')
        .replace(/\*(.*?)\*/g, '<em class="text-stone-300 italic font-serif">$1</em>')
        .replace(/`(.*?)`/g, '<code class="bg-black/40 text-[#ff4d00] font-mono text-[11px] px-1.5 py-0.5 rounded-none">$1</code>');
      result.push(
        <p key={i} className="text-stone-300 text-[12.5px] mb-2 leading-relaxed"
          dangerouslySetInnerHTML={{ __html: rendered }} />
      );
      i++;
    }
    return result;
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-4xl max-h-[88vh] mx-4 bg-[#0d0d0d] border border-white/15 flex flex-col shadow-2xl">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/15 bg-[#161616] select-none">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[#ff4d00]/10 border border-[#ff4d00]/30 flex items-center justify-center">
              <span className="material-symbols-outlined text-[18px] text-[#ff4d00]">fact_check</span>
            </div>
            <div>
              <h2 className="text-[13px] font-bold text-white uppercase tracking-widest">Rubric Đánh Giá</h2>
              <p className="text-[10px] text-stone-500 font-mono">rubric.md — tiêu chí đánh giá kết quả gen</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Download */}
            <button
              onClick={handleDownload}
              title="Download rubric.md"
              className="flex items-center gap-1.5 px-3 py-1.5 text-stone-400 border border-white/10 hover:border-white/20 hover:text-white text-[10px] uppercase tracking-wider font-bold transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[15px]">download</span>
              Export
            </button>

            {/* Reset */}
            <button
              onClick={handleReset}
              title="Reset về mặc định"
              className="flex items-center gap-1.5 px-3 py-1.5 text-stone-400 border border-white/10 hover:border-rose-500/40 hover:text-rose-400 text-[10px] uppercase tracking-wider font-bold transition-all cursor-pointer"
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
              className="p-1.5 text-stone-500 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
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
              className="w-full h-full min-h-[60vh] bg-[#080808] text-stone-200 font-mono text-[12.5px] p-6 resize-none outline-none focus:ring-0 border-none leading-relaxed custom-scrollbar"
              spellCheck={false}
            />
          ) : (
            <div className="overflow-y-auto max-h-[68vh] p-6 custom-scrollbar">
              {renderMarkdown(content)}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-white/10 bg-black/20 flex items-center justify-between select-none">
          <span className="text-[10px] text-stone-600 font-mono">
            {content.length} ký tự · {content.split('\n').length} dòng
          </span>
          <span className="text-[10px] text-stone-600 font-mono uppercase tracking-widest">
            Lưu trong trình duyệt · không sync với server
          </span>
        </div>
      </div>
    </div>
  );
}
