import React from "react";

interface HeaderProps {
  currentStep: number;
  onStepChange?: (step: number) => void;
  onRunTest: () => void;
}

export default function Header({ currentStep, onRunTest }: HeaderProps) {
  const getStepLabel = () => {
    switch (currentStep) {
      case 1:
        return "Workspace: Data Ingestion & Log Discovery";
      case 2:
        return "Workspace: Curating Customer Intents Matrix";
      case 3:
        return "Workspace: User Persona Simulation Playground";
      case 4:
        return "Workspace: Active Test Scenarios & Test Cases";
      default:
        return "Active Diagnostic Workspace";
    }
  };

  return (
    <header className="h-16 bg-[#ffffff] flex items-center justify-between px-8 sticky top-0 z-40 border-b border-stone-200">
      {/* Contextual Workspace Label */}
      <div className="flex items-center gap-3">
        <div className="w-1.5 h-1.5 bg-[#ff4d00] animate-pulse"></div>
        <span className="text-[10.5px] font-mono uppercase tracking-[0.18em] font-bold text-stone-800">
          {getStepLabel()}
        </span>
      </div>

      {/* Right corner controls */}
      <div className="flex items-center gap-4">
      </div>
    </header>
  );
}
