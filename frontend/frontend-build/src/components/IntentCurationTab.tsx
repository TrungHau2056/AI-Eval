import React, { useState } from 'react';
import { Intent } from '../types';
import * as api from '../api/client';

interface Props {
  intents: Intent[];
  setIntents: (i: Intent[]) => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  onApproved: () => void;
  apiKey: string;
  aiModel: string;
}

export default function IntentCurationTab({ intents, setIntents, showToast, onApproved, apiKey, aiModel }: Props) {
  const [search, setSearch] = useState('');
  const [regenerating, setRegenerating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [guidance, setGuidance] = useState('');
  const [showGuidance, setShowGuidance] = useState(false);

  const visible = intents.filter((i) => i.status !== 'deleted').filter((i) => {
    const t = search.toLowerCase();
    return i.context.toLowerCase().includes(t) || i.goal.toLowerCase().includes(t);
  });

  const updateIntent = (id: string, patch: Partial<Intent>) => {
    const updated = intents.map((i) => i.id === id ? { ...i, ...patch, status: 'edited' as const } : i);
    setIntents(updated);
    api.updateIntents([{ id, ...patch }]).catch(() => {});
  };

  const deleteIntent = (id: string) => {
    const updated = intents.map((i) => i.id === id ? { ...i, status: 'deleted' as const } : i);
    setIntents(updated);
    api.updateIntents([{ id, status: 'deleted' }]).catch(() => {});
  };

  const addIntent = () => {
    const newIntent: Intent = {
      id: `custom-${Date.now()}`,
      context: 'Bối cảnh mới',
      goal: 'Mục tiêu mới',
      evidence: [],
      status: 'edited',
    };
    setIntents([newIntent, ...intents]);
  };

  const handleRegenerate = async () => {
    if (!apiKey) { showToast('Cần nhập API key.', 'error'); return; }
    setRegenerating(true);
    try {
      const result = await api.regenerateIntents(aiModel, apiKey, guidance);
      setIntents(result);
      showToast('Đã regenerate Intent thành công!', 'success');
      setShowGuidance(false);
      setGuidance('');
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setRegenerating(false);
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      // Push edits first
      const patches = intents.filter(i => i.status === 'edited').map(i => ({
        id: i.id, context: i.context, goal: i.goal, status: i.status,
      }));
      if (patches.length) await api.updateIntents(patches);
      await api.approveIntents();
      const fresh = await api.getIntents();
      setIntents(fresh);
      showToast(`${fresh.filter((i: Intent) => i.status === 'approved').length} Intent đã được chốt!`, 'success');
      onApproved();
    } catch (e: any) {
      showToast(e.message, 'error');
    } finally {
      setApproving(false);
    }
  };

  const getTraitBadge = (i: number) => {
    const colors = [
      'bg-[#ff4d00]/20 text-[#ff4d00] border-[#ff4d00]/30',
      'bg-blue-950/40 text-blue-400 border-blue-900/30',
      'bg-emerald-950/40 text-emerald-400 border-emerald-900/30',
      'bg-fuchsia-950/40 text-fuchsia-400 border-fuchsia-900/30',
      'bg-rose-950/40 text-rose-400 border-rose-900/30',
    ];
    return colors[i % colors.length];
  };

  return (
    <div className="max-w-[1400px] mx-auto bg-[#161616] border border-white/15 overflow-hidden flex flex-col h-[calc(100vh-280px)] rounded-none">
      
      {/* Toolbar */}
      <div className="px-6 py-4 border-b border-white/15 flex items-center justify-between bg-black/20 gap-4 select-none">
        <div className="flex items-center gap-4">
          <h2 className="text-[13px] font-bold text-white uppercase tracking-[0.2em]">Intent Review</h2>
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-stone-500 text-[18px]">search</span>
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm intent..."
              className="pl-9 pr-4 py-1.5 bg-black/40 border border-white/10 text-[12px] w-56 focus:ring-1 focus:ring-[#ff4d00] focus:border-[#ff4d00] outline-none rounded-none text-white placeholder-stone-600"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Regenerate */}
          <button onClick={() => setShowGuidance(!showGuidance)}
            className="flex items-center gap-2 px-4 py-2 text-stone-300 border border-white/15 hover:border-white/30 hover:text-white text-[11px] uppercase tracking-wider font-bold transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">refresh</span>
            Regenerate
          </button>

          {/* Add */}
          <button onClick={addIntent}
            className="flex items-center gap-2 px-4 py-2 text-[#ff4d00] border border-[#ff4d00]/50 hover:bg-[#ff4d00]/10 text-[11px] uppercase tracking-wider font-bold transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">add</span>
            Thêm
          </button>

          {/* Approve */}
          <button onClick={handleApprove} disabled={approving || visible.length === 0}
            className="flex items-center gap-2 px-6 py-2 bg-[#ff4d00] text-white text-[11px] uppercase tracking-wider font-bold hover:opacity-95 transition-all disabled:opacity-40 cursor-pointer"
          >
            {approving ? (
              <><span className="material-symbols-outlined animate-spin text-[16px]">sync</span>Đang chốt...</>
            ) : (
              <><span className="material-symbols-outlined text-[16px]">check_circle</span>Chốt Intent → Bước 2</>
            )}
          </button>
        </div>
      </div>

      {/* Guidance row */}
      {showGuidance && (
        <div className="px-6 py-3 border-b border-[#ff4d00]/20 bg-[#ff4d00]/5 flex items-center gap-3">
          <span className="material-symbols-outlined text-[18px] text-[#ff4d00]">tips_and_updates</span>
          <input
            type="text"
            value={guidance}
            onChange={(e) => setGuidance(e.target.value)}
            placeholder="Hướng dẫn thêm cho AI (VD: Tập trung vào intent liên quan đến đặt lịch học)"
            className="flex-grow bg-black/40 border border-white/10 text-[12px] px-3 py-2 text-white outline-none focus:ring-1 focus:ring-[#ff4d00] font-mono placeholder-stone-600"
          />
          <button onClick={handleRegenerate} disabled={regenerating}
            className="px-5 py-2 bg-[#ff4d00] text-white text-[11px] font-bold uppercase tracking-wider hover:opacity-90 transition-all disabled:opacity-50 cursor-pointer flex items-center gap-2"
          >
            {regenerating ? <span className="material-symbols-outlined animate-spin text-[16px]">sync</span> : <span className="material-symbols-outlined text-[16px]">send</span>}
            Chạy
          </button>
        </div>
      )}

      {/* Table */}
      <div className="flex-grow overflow-auto custom-scrollbar">
        <table className="w-full text-left border-collapse">
          <thead className="sticky top-0 bg-[#0d0d0d] z-10">
            <tr className="border-b border-white/15 text-stone-400 font-bold text-[10px] uppercase tracking-wider">
              <th className="px-4 py-3 w-8 font-mono text-center">#</th>
              <th className="px-4 py-3 w-[280px]">Context (Bối cảnh)</th>
              <th className="px-4 py-3">Goal (Mục tiêu)</th>
              <th className="px-4 py-3 w-20 text-center">Status</th>
              <th className="px-4 py-3 w-12"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-stone-200">
            {visible.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-16 text-stone-500 text-xs font-serif italic">
                  Chưa có intent. Quay lại Bước 1 để chạy Intent Discovery.
                </td>
              </tr>
            ) : (
              visible.map((item, idx) => (
                <tr key={item.id} className="group hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-block w-6 h-6 text-[9px] font-bold font-mono flex items-center justify-center border ${getTraitBadge(idx)}`}>
                      {idx + 1}
                    </span>
                  </td>

                  <td className="px-4 py-2">
                    <textarea
                      value={item.context}
                      onChange={(e) => updateIntent(item.id, { context: e.target.value })}
                      rows={2}
                      className="bg-transparent border-none p-0 text-[12.5px] text-white w-full focus:ring-0 focus:outline-none resize-none leading-relaxed focus:border-b focus:border-[#ff4d00]/50"
                    />
                  </td>

                  <td className="px-4 py-2">
                    <textarea
                      value={item.goal}
                      onChange={(e) => updateIntent(item.id, { goal: e.target.value })}
                      rows={2}
                      className="bg-transparent border-none p-0 text-[12.5px] text-stone-300 italic font-serif w-full focus:ring-0 focus:outline-none resize-none leading-relaxed"
                    />
                  </td>

                  <td className="px-4 py-3 text-center">
                    <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 border ${
                      item.status === 'approved' ? 'text-emerald-400 border-emerald-800 bg-emerald-950/30' :
                      item.status === 'edited' ? 'text-yellow-400 border-yellow-800 bg-yellow-950/30' :
                      'text-stone-400 border-stone-700 bg-stone-800/50'
                    }`}>
                      {item.status}
                    </span>
                  </td>

                  <td className="px-4 py-3 text-right">
                    <button onClick={() => deleteIntent(item.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-rose-950/50 text-stone-500 hover:text-rose-400 cursor-pointer"
                      title="Xóa intent"
                    >
                      <span className="material-symbols-outlined text-[18px]">delete</span>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="px-6 py-3 border-t border-white/15 flex items-center justify-between bg-black/20 select-none">
        <span className="text-[12px] text-stone-400 font-serif italic">
          {visible.length} intents · {intents.filter(i => i.status === 'approved').length} đã chốt
        </span>
        <span className="text-[10px] text-stone-600 font-mono uppercase tracking-widest">
          Bấm vào ô để chỉnh sửa trực tiếp
        </span>
      </div>
    </div>
  );
}
