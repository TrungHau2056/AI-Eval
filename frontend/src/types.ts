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
  prdSource?: string; // verbatim PRD excerpt (raw_observation) for prd-explicit intents
  // Merge-aware: a merged intent carries multiple source labels + multiple PRD quotes.
  sources?: string[]; // e.g. ["prd","data"] | ["prd_inferred"] | ["data"]
  prdSources?: string[]; // up to 3 verbatim PRD excerpts
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

export interface PersonaIssue {
  score: number;
  maxScore: number;
  reason: string;
  fixes: string[];
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
