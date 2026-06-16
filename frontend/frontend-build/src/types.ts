// ─── Backend models (match FastAPI schemas.py) ───────────────────────────────

export interface Intent {
  id: string;
  context: string;
  goal: string;
  evidence: string[];
  status: 'generated' | 'edited' | 'approved' | 'deleted';
}

export interface Persona {
  id: string;
  intent_id: string;
  name: string;
  description: string;
  trait_type: 'easy' | 'hard';
  status: 'generated' | 'edited' | 'approved' | 'deleted';
}

export interface TestCasePrompt {
  id: string;
  persona_id: string;
  intent_id: string;
  prompt_text: string;
  status: 'generated' | 'edited' | 'approved' | 'deleted';
}

export interface PipelineState {
  raw_input: RawInput | null;
  intents: Intent[];
  personas: Persona[];
  test_prompts: TestCasePrompt[];
  current_step: number;
}

export interface RawInput {
  id: string;
  source_type: 'csv' | 'text';
  content: string;
  metadata: Record<string, string>;
}

// ─── UI-only helpers ──────────────────────────────────────────────────────────

export type ToastType = 'success' | 'error' | 'info';

export interface Toast {
  message: string;
  type: ToastType;
}
