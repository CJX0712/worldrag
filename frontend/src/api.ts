import type { EvalResponse, Health, QueryResponse } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(body.detail ?? `HTTP ${resp.status}`);
  }
  return body as T;
}

export const api = {
  health: () => request<Health>("/health"),
  ingestSamples: (texts: Array<{ text: string; doc_id?: string }>) =>
    request<{ ingested_chunks: number; total_chunks: number }>("/ingest", {
      method: "POST",
      body: JSON.stringify({ texts, paths: [] }),
    }),
  query: (query: string) =>
    request<QueryResponse>("/query", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
  evaluate: () => request<EvalResponse>("/evaluate", { method: "POST" }),
};
