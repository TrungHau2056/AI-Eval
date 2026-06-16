import React from 'react';

// Minimal markdown renderer for headings, tables, bold, italic, blockquote, lists.
// Shared by RubricModal and GuidelinePanel. Light-theme styling.
export function renderMarkdown(md: string): React.ReactNode[] {
  const lines = md.split('\n');
  const result: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // H1
    if (line.startsWith('# ')) {
      result.push(<h1 key={i} className="text-[18px] font-bold text-stone-900 mb-4 mt-2 tracking-tight">{line.slice(2)}</h1>);
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
      result.push(<h3 key={i} className="text-[12px] font-bold text-stone-700 mb-2 mt-4">{line.slice(4)}</h3>);
      i++; continue;
    }
    // HR
    if (line.startsWith('---')) {
      result.push(<hr key={i} className="border-black/10 my-6" />);
      i++; continue;
    }
    // Blockquote
    if (line.startsWith('> ')) {
      result.push(
        <blockquote key={i} className="border-l-2 border-[#ff4d00]/50 pl-4 py-1 my-2 text-stone-500 text-[12px] font-serif italic bg-[#ff4d00]/5">
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
              <tr className="border-b border-black/10 text-stone-500 text-[10px] uppercase tracking-wider">
                {headers.map((h, hi) => (
                  <th key={hi} className="py-2 px-3 font-bold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-black/5">
              {rows.map((row, ri) => (
                <tr key={ri} className="hover:bg-black/[0.02] transition-colors">
                  {row.map((cell, ci) => (
                    <td key={ci} className={`py-2 px-3 ${ci === 0 ? 'font-bold text-[#ff4d00] font-mono' : 'text-stone-700'}`}>
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
        <li key={i} className="text-stone-700 text-[12.5px] ml-4 mb-1 list-disc list-inside font-serif">
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
    // Paragraph with inline bold/italic/code
    const rendered = line
      .replace(/\*\*(.*?)\*\*/g, '<strong class="text-stone-900 font-bold">$1</strong>')
      .replace(/\*(.*?)\*/g, '<em class="text-stone-600 italic font-serif">$1</em>')
      .replace(/`(.*?)`/g, '<code class="bg-stone-100 text-[#ff4d00] font-mono text-[11px] px-1.5 py-0.5 rounded-none">$1</code>');
    result.push(
      <p key={i} className="text-stone-700 text-[12.5px] mb-2 leading-relaxed"
        dangerouslySetInnerHTML={{ __html: rendered }} />
    );
    i++;
  }
  return result;
}
