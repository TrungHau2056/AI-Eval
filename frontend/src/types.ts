export interface SourcePost {
  url: string;
  username: string;
  platform: string;
  textExcerpt: string;
}

export interface Intent {
  id: string;
  name: string;
  phase: string;
  utterance: string;
  triggerMoment: string;
  selected: boolean;
  // Gap analysis (Phase 1)
  source?: 'data' | 'prd' | 'prd_inferred';
  coverage?: '' | 'confirmed' | 'prd_only' | 'data_only';
  matchedIds?: string[];
  sourcePosts?: SourcePost[];
}

export interface IngestSource {
  source_type: string;
  filename: string;
  rows_in: number;
  rows_after_dedup: number;
  status: string;
}

export interface IngestStats {
  sources: IngestSource[];
  prd_loaded: boolean;
  total_chars: number;
  warnings: string[];
}

export interface CostSummary {
  run_id?: string | null;
  event_count?: number;
  openai_event_count?: number;
  apify_event_count?: number;
  openai_estimated_usd?: number | null;
  apify_actual_usd?: number | null;
  total_usd?: number | null;
  price_missing_count?: number;
  missing_cost_count?: number;
  started_at?: string | null;
  last_event_at?: string | null;
  ended_at?: string | null;
  closed?: boolean;
}

export interface Persona {
  id: string;
  intentId?: string;
  type: 'happy' | 'edge';
  name: string;
  trigger: string;
  utterance: string;
  frequency: number; // percentage (0 - 100)
  frequencyText?: string; // raw text from pipeline e.g. "2-3 lần/tuần"
  pain: string;
  reject: string;
  expectedAIBehavior?: string;
}

export interface TestCase {
  id: string;
  intentName: string;
  personaName: string;
  simulatedPrompt: string;
  expectedOutcome: string;
  selected: boolean;
  status?: 'pending' | 'running' | 'passed' | 'failed';
  logs?: string[];
  goal?: string;
}
