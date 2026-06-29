import { Intent, Persona } from "../types";
import { downloadTextFile } from "./exportIntents";

function personaToExportRow(persona: Persona, intents: Intent[]) {
  const intent = intents.find((i) => i.id === persona.intentId);
  return {
    id: persona.id,
    intent_id: persona.intentId ?? "",
    intent_name: intent?.name ?? "",
    type: persona.type,
    name: persona.name,
    trigger: persona.trigger,
    utterance: persona.utterance,
    frequency: persona.frequency,
    frequency_text: persona.frequencyText ?? "",
    pain: persona.pain,
    reject: persona.reject,
    expected_ai_behavior: persona.expectedAIBehavior ?? "",
  };
}

export function buildPersonasJson(personas: Persona[], intents: Intent[]): string {
  const payload = {
    exportedAt: new Date().toISOString(),
    count: personas.length,
    personas: personas.map((persona) => personaToExportRow(persona, intents)),
  };
  return JSON.stringify(payload, null, 2);
}

export function downloadPersonasJson(personas: Persona[], intents: Intent[]) {
  downloadTextFile(buildPersonasJson(personas, intents), "personas.json", "application/json");
}
