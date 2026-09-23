export interface Citation {
  n: number;
  doc_id: string;
  chunk_id: string;
  score: number;
  source: string;
  snippet: string;
}

export interface QueryResponse {
  query: string;
  answer: string;
  citations: Citation[];
  backends: Record<string, string>;
}

export interface Health {
  status: string;
  chunks: number;
  backends: Record<string, string>;
}

export interface EvalMetrics {
  recall_at_k: number;
  mrr: number;
  keyword_hit_rate: number;
  queries: number;
  chunks: number;
}

export interface EvalResponse {
  metrics: EvalMetrics;
  backends: Record<string, string>;
  degradations: Record<string, string>;
  per_query: Array<{
    query: string;
    hit: boolean;
    rank: number | null;
    keyword_hit: boolean;
    retrieved: string[];
  }>;
}

export interface ChatTurn {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  error?: boolean;
}
