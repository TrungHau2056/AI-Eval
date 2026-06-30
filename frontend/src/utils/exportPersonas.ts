import { Persona, Intent } from "../types";
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
    frequency: persona.frequency ?? "",
    frequency_text: persona.frequencyText ?? "",
    pain: persona.pain,
    reject: persona.reject,
    expected_ai_behavior: persona.expectedAIBehavior ?? "",
  };
}

export function buildPersonasJson(personas: Persona[]): string {
  const payload = {
    exportedAt: new Date().toISOString(),
    count: personas.length,
    personas,
  };
  return JSON.stringify(payload, null, 2);
}

export function buildPersonasCsv(personas: Persona[], intents: Intent[]): string {
  const headers = [
    "id",
    "intent_id",
    "intent_name",
    "type",
    "name",
    "trigger",
    "utterance",
    "frequency",
    "frequency_text",
    "pain",
    "reject",
    "expected_ai_behavior",
  ];

  const escape = (value: string | number | boolean) => {
    const text = String(value ?? "");
    if (/[",\n\r]/.test(text)) {
      return `"${text.replace(/"/g, '""')}"`;
    }
    return text;
  };

  const rows = personas.map((persona) => {
    const row = personaToExportRow(persona, intents);
    return headers.map((key) => escape(row[key as keyof typeof row] as string | number | boolean)).join(",");
  });

  return [headers.join(","), ...rows].join("\n");
}

export function downloadPersonasJson(personas: Persona[]) {
  downloadTextFile(buildPersonasJson(personas), "personas.json", "application/json");
}

export function downloadPersonasCsv(personas: Persona[], intents: Intent[]) {
  downloadTextFile(buildPersonasCsv(personas, intents), "personas.csv", "text/csv");
}
