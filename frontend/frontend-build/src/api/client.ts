// API client — wraps all FastAPI backend endpoints at /api/*
// Backend runs at localhost:8000 in dev; same-origin in prod.

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? 'Request failed');
  }
  return res.json();
}

// ─── State ────────────────────────────────────────────────────────────────────
export const getState = () => req<any>('/api/state');
export const resetState = () => req<any>('/api/state/reset', { method: 'POST' });

// ─── Input ────────────────────────────────────────────────────────────────────
export const submitText = (content: string) =>
  req<any>('/api/input/text', { method: 'POST', body: JSON.stringify({ content }) });

export const submitCSV = (formData: FormData) =>
  fetch(`${BASE}/api/input/csv`, { method: 'POST', body: formData }).then(async (r) => {
    if (!r.ok) throw new Error((await r.json()).detail);
    return r.json();
  });

// ─── Intents ──────────────────────────────────────────────────────────────────
export const extractIntents = (model: string, api_key: string) =>
  req<any>('/api/intents/extract', { method: 'POST', body: JSON.stringify({ model, api_key }) });

export const getIntents = () => req<any[]>('/api/intents');

export const updateIntents = (updates: any[]) =>
  req<any>('/api/intents', { method: 'PUT', body: JSON.stringify({ updates }) });

export const approveIntents = () =>
  req<any>('/api/intents/approve', { method: 'POST' });

export const regenerateIntents = (model: string, api_key: string, guidance: string) =>
  req<any[]>('/api/intents/regenerate', {
    method: 'POST',
    body: JSON.stringify({ model, api_key, guidance }),
  });

// ─── Personas ─────────────────────────────────────────────────────────────────
export const generatePersonas = (model: string, api_key: string, guidance = '') =>
  req<any[]>('/api/personas/generate', {
    method: 'POST',
    body: JSON.stringify({ model, api_key, guidance }),
  });

export const getPersonas = () => req<any[]>('/api/personas');

export const updatePersonas = (updates: any[]) =>
  req<any>('/api/personas', { method: 'PUT', body: JSON.stringify({ updates }) });

export const approvePersonas = () =>
  req<any>('/api/personas/approve', { method: 'POST' });

export const regeneratePersonas = (model: string, api_key: string, guidance: string) =>
  req<any[]>('/api/personas/regenerate', {
    method: 'POST',
    body: JSON.stringify({ model, api_key, guidance }),
  });

// ─── Test Prompts ─────────────────────────────────────────────────────────────
export const generatePrompts = (model: string, api_key: string, guidance = '') =>
  req<any[]>('/api/prompts/generate', {
    method: 'POST',
    body: JSON.stringify({ model, api_key, guidance }),
  });

export const getPrompts = () => req<any[]>('/api/prompts');

export const updatePrompts = (updates: any[]) =>
  req<any>('/api/prompts', { method: 'PUT', body: JSON.stringify({ updates }) });

export const regeneratePrompts = (model: string, api_key: string, guidance: string) =>
  req<any[]>('/api/prompts/regenerate', {
    method: 'POST',
    body: JSON.stringify({ model, api_key, guidance }),
  });

// ─── Export ───────────────────────────────────────────────────────────────────
export const exportCsv = () => `${BASE}/api/export/csv`;
export const exportMarkdown = () => `${BASE}/api/export/markdown`;
