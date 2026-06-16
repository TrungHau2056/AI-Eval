// ─── Backend models (match FastAPI schemas.py) ───────────────────────────────

export interface Intent {
  id: string;
  context: string;
  goal: string;
  evidence: string[];
  status: 'generated' | 'edited' | 'approved' | 'deleted';
  // UI-only fields (not persisted by the backend)
  phase?: string;
  utterance?: string;
}

export interface Persona {
  id: string;
  intent_id: string;
  name: string;
  description: string;
  trait_type: 'easy' | 'hard';
  status: 'generated' | 'edited' | 'approved' | 'deleted';
  // UI-only rich fields (mock, not persisted by the backend).
  // Each persona is generated from a single sub-intent.
  sub_intent_id?: string;
  sub_intent_num?: number;
  sub_intent_name?: string;
  persona_num?: number;
  persona_type?: string;
  user_profile?: string;
  estimated_user_ratio?: string;
  usage_frequency?: string;
  reason_to_use?: string;
  sample_start_query?: string;
  special_situation?: string;
  why_this_persona_is_different?: string;
  expected_behavior_or_need?: string;
  not_needed?: string;
}

export interface TestCasePrompt {
  id: string;
  persona_id: string;
  intent_id: string;
  prompt_text: string;
  status: 'generated' | 'edited' | 'approved' | 'deleted';
}

// ─── UI-only (mock, no backend) ───────────────────────────────────────────────
export interface SubIntent {
  id: string;
  intent_id: string;
  title: string;
  description: string;
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
