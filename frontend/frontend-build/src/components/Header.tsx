import React from 'react';

interface HeaderProps {
  currentStep: number;
  onStepChange: (step: number) => void;
  onOpenRubric: () => void;
}

export default function Header({ currentStep, onStepChange, onOpenRubric }: HeaderProps) {
  const tabs = [
    { step: 1, label: 'Data Ingestion' },
    { step: 2, label: 'Intent Curation' },
    { step: 3, label: 'Sub-Intent' },
    { step: 4, label: 'Persona Playground' },
    { step: 5, label: 'Export' },
    { step: 6, label: 'Single-turn' },
    { step: 7, label: 'Dashboard' },
  ];

  return (
    <header className="h-16 bg-white flex items-center justify-between px-8 sticky top-0 z-40 border-b border-black/10">
      {/* Tab Navigation */}
      <nav className="flex items-center gap-6 h-full">
        {/* {tabs.map(({ step, label }) => (
          <button
            key={step}
            onClick={() => onStepChange(step)}
            type="button"
            className={`cursor-pointer text-[11px] uppercase tracking-[0.2em] font-bold h-full flex items-center transition-all ${
              currentStep === step
                ? 'text-[#ff4d00] border-b-2 border-[#ff4d00]'
                : 'text-stone-500 hover:text-stone-900'
            }`}
          >
            {label}
          </button>
        ))} */}
      </nav>

      {/* Right controls */}
      <div className="flex items-center gap-3">
        {/* Rubric Button */}
        <button
          onClick={onOpenRubric}
          type="button"
          title="Mở rubric đánh giá"
          className="flex items-center gap-2 px-4 py-2 border border-[#ff4d00]/50 text-[#ff4d00] hover:bg-[#ff4d00]/10 rounded-none font-bold text-[11px] uppercase tracking-wider transition-all cursor-pointer"
        >
          <span className="material-symbols-outlined text-[17px]">fact_check</span>
          Rubric
        </button>

        {/* Notifications */}
        <button
          type="button"
          className="p-2 text-stone-500 hover:text-stone-900 hover:bg-black/5 rounded-none transition-colors relative"
        >
          <span className="material-symbols-outlined text-[23px]">notifications</span>
          <span className="absolute top-2 right-2 w-2 h-2 bg-[#ff4d00] rounded-none border border-white" />
        </button>

        {/* Avatar */}
        <div className="w-9 h-9 overflow-hidden border border-black/10 hover:border-[#ff4d00] cursor-pointer transition-colors bg-[#ff4d00]/20 flex items-center justify-center">
          <span className="material-symbols-outlined text-[20px] text-[#ff4d00]">person</span>
        </div>
      </div>
    </header>
  );
}
