import React from "react";

interface StepIndicatorProps {
  currentStep: number;
  onStepChange: (step: number) => void;
}

export default function StepIndicator({ currentStep, onStepChange }: StepIndicatorProps) {
  // Compute progress line width based on currentStep
  const getProgressWidth = () => {
    switch (currentStep) {
      case 1:
        return "w-[0%]";
      case 2:
        return "w-[33%]";
      case 3:
        return "w-[66%]";
      case 4:
        return "w-[100%]";
      default:
        return "w-[0%]";
    }
  };

  const steps = [
    { num: 1, label: "1. Data Ingestion" },
    { num: 2, label: "2. Intent Curation" },
    { num: 3, label: "3. Persona Playground" },
    { num: 4, label: "4. Test Case" },
  ];

  return (
    <div className="max-w-5xl mx-auto mb-10 px-8 select-none">
      <div className="flex items-center justify-between relative">
          {/* Progress Line Background */}
          <div className="absolute top-5 left-10 right-10 h-[1px] bg-stone-200 -z-10"></div>
          {/* Active Progress Line */}
          <div
            className={`absolute top-5 left-10 h-[1px] bg-[#ff4d00] -z-10 transition-all duration-500 ease-out`}
            style={{
              width: currentStep === 1 ? "0%" : currentStep === 2 ? "33%" : currentStep === 3 ? "66%" : "100%",
            }}
          ></div>

          {/* Steps */}
          {steps.map((st) => {
            const isCompleted = st.num < currentStep;
            const isActive = st.num === currentStep;

            return (
              <button
                key={st.num}
                onClick={() => onStepChange(st.num)}
                className="flex flex-col items-center gap-2 bg-[#f8f9fa] px-4 cursor-pointer focus:outline-none focus:ring-0 group"
              >
                {isCompleted ? (
                  // Completed Step
                  <div className="w-10 h-10 rounded-none bg-[#ff4d00] flex items-center justify-center text-white shadow-none ring-4 ring-[#f8f9fa] transition-transform duration-300 group-hover:scale-105">
                    <span className="material-symbols-outlined text-[20px] font-bold" style={{ fontVariationSettings: "'FILL' 1" }}>
                      check
                    </span>
                  </div>
                ) : isActive ? (
                  // Active Step
                  <div className="w-10 h-10 rounded-none bg-white border-[2px] border-[#ff4d00] flex items-center justify-center shadow-none ring-4 ring-[#f8f9fa] relative">
                    <div className="w-3.5 h-3.5 bg-[#ff4d00]"></div>
                  </div>
                ) : (
                  // Upcoming Step
                  <div className="w-10 h-10 rounded-none bg-white border border-stone-200 flex items-center justify-center text-stone-400 ring-4 ring-[#f8f9fa] transition-colors duration-300 group-hover:bg-stone-50">
                    <span className="text-[12px] font-bold font-mono">{st.num}</span>
                  </div>
                )}

                {/* Step Label */}
                <span
                  className={`text-[11px] uppercase tracking-wider transition-colors duration-300 ${
                    isActive
                      ? "font-bold text-[#ff4d00]"
                      : isCompleted
                      ? "text-stone-700 font-medium"
                      : "text-stone-400 font-medium"
                  }`}
                >
                  {st.label}
                </span>
              </button>
            );
          })}
      </div>
    </div>
  );
}
