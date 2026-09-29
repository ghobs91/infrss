/**
 * Layman summary — a structured plain-language translation of a primary-source document.
 *
 * Generated on-device (WebLLM), by a local Ollama endpoint, or by the server fallback, then
 * shared across users because it is stored against the article's shared content row.
 */

export interface LaymanSummaryInput {
  headline: string;
  what_happened: string[];
  key_impact: string;
  model_identifier: string;
}

export interface LaymanSummary extends LaymanSummaryInput {
  generated_at: string;
}
