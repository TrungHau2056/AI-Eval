import React from "react";
import { CostSummary } from "../types";

interface HeaderProps {
  currentStep: number;
  onStepChange?: (step: number) => void;
  onRunTest: () => void;
  costSummary?: CostSummary | null;
}

const formatUsd = (value?: number | null): string => {
  if (value === null || value === undefined) return "--";
  const digits = Math.abs(value) < 0.01 ? 6 : 4;
  return `$${value.toFixed(digits)}`;
};

export default function Header({ currentStep, onRunTest, costSummary }: HeaderProps) {
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

  const hasCostEvents = (costSummary?.event_count ?? 0) > 0;
  const priceMissing = (costSummary?.price_missing_count ?? 0) > 0;

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
        <div
          className={`flex items-center gap-2 border px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest ${
            priceMissing
              ? "border-amber-300 bg-amber-50 text-amber-700"
              : "border-stone-200 bg-stone-50 text-stone-700"
          }`}
          title={priceMissing ? "OpenAI price config missing" : "Total end-to-end run cost"}
        >
          <span className="material-symbols-outlined text-[15px]">
            {priceMissing ? "warning" : "payments"}
          </span>
          <span className="font-bold">
            {priceMissing ? "Price Missing" : `Total Run ${hasCostEvents ? formatUsd(costSummary?.total_usd) : "--"}`}
          </span>
        </div>
      </div>
    </header>
  );
}
