// Mirrors backend/app/schemas.py. Keep in sync.

export type Modality = "text" | "url" | "image" | "audio" | "batch";
export type ConfidenceBand = "high" | "moderate" | "low";
export type Verdict = "real" | "fake";
export type CredibilityTier = "high" | "mixed" | "low" | "satire" | "state";

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface SignalWord {
  word: string;
  weight: number;
  direction: Verdict;
}

export interface SourceCredibility {
  domain: string;
  tier: CredibilityTier;
  label: string;
  blurb: string;
}

export interface Citation {
  id: string;
  title: string;
  source: string;
  snippet: string;
  score: number;
}

export interface PredictResponse {
  label: Verdict;
  confidence: number;
  confidence_band: ConfidenceBand;
  probabilities: { fake: number; real: number };
  mode: string;
  modality: Modality;
  signal_words: SignalWord[];
  source_title: string | null;
  source_credibility: SourceCredibility | null;
  citations: Citation[];
  analyzed_text: string;
  extracted_text: string | null;
  transcript: string | null;
  media_observations: string | null;
  verdict_source: "llm" | "classic_fallback";
  llm_reasoning: string | null;
}

export interface HistoryItem {
  id: number;
  source_type: string;
  source_ref: string | null;
  input_excerpt: string;
  label: string;
  confidence: number;
  mode: string;
  created_at: string;
}

export interface BatchResultRow {
  text_excerpt: string;
  label: string;
  confidence: number;
  confidence_band: ConfidenceBand;
  source_ref: string | null;
  signal_words: SignalWord[];
}

export interface BatchResponse {
  results: BatchResultRow[];
  total: number;
  fake_count: number;
  real_count: number;
  combined_text: string;
  extraction_summary: Record<string, unknown> | null;
}

export interface BatchJobStatus {
  job_id: string;
  state: "pending" | "running" | "complete" | "error";
  processed: number;
  total: number;
  error: string | null;
  result: BatchResponse | null;
}

export interface ModelMetric {
  algorithm: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
}

export interface AnalyticsSummary {
  total_predictions: number;
  fake_count: number;
  real_count: number;
  fake_ratio: number;
  average_confidence: number;
  by_day: { date: string; fake: number; real: number }[];
  by_mode: Record<string, number>;
  by_modality: Record<string, number>;
  model_metrics: {
    classic?: ModelMetric;
    advanced?: ModelMetric;
    dataset_size?: number;
    trained_at?: string;
  };
}

export interface RagStatus {
  enabled: boolean;
  ready: boolean;
  total_chunks: number;
  media_literacy_docs: number;
  fact_check_entries: number;
  built_at: string | null;
}
