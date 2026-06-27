import { Intent } from "../types";

function intentToExportRow(intent: Intent) {
  return {
    id: intent.id,
    name: intent.name,
    phase: intent.phase,
    utterance: intent.utterance,
    trigger_moment: intent.triggerMoment,
    source: intent.source ?? "",
    coverage: intent.coverage ?? "",
    selected: intent.selected,
    matched_ids: (intent.matchedIds ?? []).join("; "),
  };
}

export function buildIntentsJson(intents: Intent[]): string {
  const payload = {
    exportedAt: new Date().toISOString(),
    count: intents.length,
    intents: intents.map((intent) => ({
      ...intent,
      triggerMoment: intent.triggerMoment,
    })),
  };
  return JSON.stringify(payload, null, 2);
}

export function buildIntentsCsv(intents: Intent[]): string {
  const headers = [
    "id",
    "name",
    "phase",
    "utterance",
    "trigger_moment",
    "source",
    "coverage",
    "selected",
    "matched_ids",
  ];

  const escape = (value: string | boolean) => {
    const text = String(value ?? "");
    if (/[",\n\r]/.test(text)) {
      return `"${text.replace(/"/g, '""')}"`;
    }
    return text;
  };

  const rows = intents.map((intent) => {
    const row = intentToExportRow(intent);
    return headers.map((key) => escape(row[key as keyof typeof row] as string | boolean)).join(",");
  });

  return [headers.join(","), ...rows].join("\n");
}

export function downloadTextFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function downloadIntentsJson(intents: Intent[]) {
  downloadTextFile(buildIntentsJson(intents), "extracted_intents.json", "application/json");
}

export function downloadIntentsCsv(intents: Intent[]) {
  downloadTextFile(buildIntentsCsv(intents), "extracted_intents.csv", "text/csv");
}
