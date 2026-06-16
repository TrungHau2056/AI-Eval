import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import StepIndicator from './components/StepIndicator';
import DataIngestionTab from './components/DataIngestionTab';
import IntentCurationTab from './components/IntentCurationTab';
import PersonaPlaygroundTab from './components/PersonaPlaygroundTab';
import ExportTab from './components/ExportTab';
import RubricModal from './components/RubricModal';
import { Intent, Persona, TestCasePrompt, Toast } from './types';
import * as api from './api/client';

export default function App() {
  const [currentStep, setCurrentStep] = useState(1);
  const [apiKey, setApiKey] = useState('');
  const [aiModel, setAiModel] = useState('gemini');
  const [intents, setIntents] = useState<Intent[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [prompts, setPrompts] = useState<TestCasePrompt[]>([]);
  const [toast, setToast] = useState<Toast | null>(null);
  const [isRubricOpen, setIsRubricOpen] = useState(false);

  // Load state from backend on mount
  useEffect(() => {
    api.getState()
      .then((s) => {
        if (s.current_step > 0) setCurrentStep(s.current_step);
        if (s.intents?.length) setIntents(s.intents);
        if (s.personas?.length) setPersonas(s.personas);
        if (s.test_prompts?.length) setPrompts(s.test_prompts);
      })
      .catch(() => {}); // backend not running yet → silent
  }, []);

  const showToast = (message: string, type: Toast['type'] = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // After intents approved → move to step 3 + generate personas
  const handleIntentsApproved = async () => {
    setCurrentStep(3);
    try {
      showToast('Đang gen Persona...', 'info');
      const result = await api.generatePersonas(aiModel, apiKey);
      setPersonas(result);
      showToast(`Đã gen ${result.length} persona!`, 'success');
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  // After personas approved → move to step 4 + generate prompts
  const handlePersonasApproved = async () => {
    setCurrentStep(4);
    try {
      showToast('Đang gen Test Prompt...', 'info');
      const result = await api.generatePrompts(aiModel, apiKey);
      setPrompts(result);
      showToast(`Đã gen ${result.length} test prompt!`, 'success');
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleReset = async () => {
    if (!confirm('Reset toàn bộ pipeline? Mọi dữ liệu sẽ bị xóa.')) return;
    await api.resetState().catch(() => {});
    setIntents([]);
    setPersonas([]);
    setPrompts([]);
    setCurrentStep(1);
    showToast('Đã reset workspace.', 'success');
  };

  return (
    <div className="min-h-screen bg-[#0d0d0d] text-[#e5e5e5] flex font-sans select-none">
      
      <Sidebar
        apiKey={apiKey}
        aiModel={aiModel}
        onApiKeyChange={setApiKey}
        onAiModelChange={setAiModel}
      />

      <div className="flex-1 pl-64 flex flex-col min-h-screen">
        <Header
          currentStep={currentStep}
          onStepChange={setCurrentStep}
          onOpenRubric={() => setIsRubricOpen(true)}
        />

        {/* Toast */}
        {toast && (
          <div className="fixed top-20 right-8 z-50">
            <div className={`px-5 py-3 shadow-xl flex items-center gap-2.5 text-[10px] font-mono uppercase tracking-widest border ${
              toast.type === 'success' ? 'bg-[#ff4d00] text-white border-[#ff4d00]' :
              toast.type === 'error' ? 'bg-rose-950 text-rose-200 border-rose-900' :
              'bg-stone-900 text-stone-200 border-white/15'
            }`}>
              <span className="material-symbols-outlined text-[16px]">
                {toast.type === 'success' ? 'check_circle' : toast.type === 'error' ? 'error' : 'info'}
              </span>
              <span>{toast.message}</span>
            </div>
          </div>
        )}

        <div className="flex-1 p-8">
          <StepIndicator currentStep={currentStep} onStepChange={setCurrentStep} />

          <main className="mt-2">
            {currentStep === 1 && (
              <DataIngestionTab
                onSuccess={setCurrentStep}
                showToast={showToast}
                apiKey={apiKey}
                aiModel={aiModel}
              />
            )}
            {currentStep === 2 && (
              <IntentCurationTab
                intents={intents}
                setIntents={setIntents}
                showToast={showToast}
                onApproved={handleIntentsApproved}
                apiKey={apiKey}
                aiModel={aiModel}
              />
            )}
            {currentStep === 3 && (
              <PersonaPlaygroundTab
                personas={personas}
                setPersonas={setPersonas}
                showToast={showToast}
                onApproved={handlePersonasApproved}
                apiKey={apiKey}
                aiModel={aiModel}
              />
            )}
            {currentStep === 4 && (
              <ExportTab
                prompts={prompts}
                setPrompts={setPrompts}
                intents={intents}
                personas={personas}
                showToast={showToast}
                onOpenRubric={() => setIsRubricOpen(true)}
                apiKey={apiKey}
                aiModel={aiModel}
              />
            )}
          </main>

          {/* Footer */}
          <div className="max-w-6xl mx-auto mt-8 flex justify-between items-center select-none opacity-60 hover:opacity-100 transition-opacity">
            <p className="text-[10px] text-stone-500 uppercase tracking-widest font-mono">
              AI-Eval · ui-khanh · FastAPI backend @ localhost:8000
            </p>
            <button
              onClick={handleReset}
              className="text-[10px] font-bold text-[#ff4d00] hover:underline uppercase tracking-widest font-mono flex items-center gap-1 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[13px]">restart_alt</span>
              Reset workspace
            </button>
          </div>
        </div>
      </div>

      <RubricModal isOpen={isRubricOpen} onClose={() => setIsRubricOpen(false)} />
    </div>
  );
}
