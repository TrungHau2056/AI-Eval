export interface Intent {
  id: string;
  name: string;
  phase: string;
  utterance: string;
  triggerMoment: string;
  selected: boolean;
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
