export interface ClassificationResult {
  category: string;
  priority: string;
  confidence_score: number;
}

export interface EnrichmentResult {
  core_issue: string;
  identifiers: Record<string, string>;
  urgency_signal: string;
}

export interface RoutingResult {
  destination_queue: string;
  routing_reason: string;
  escalation_flag: boolean;
  escalation_reason: string | null;
}

export interface ProcessedRecord {
  id: string;
  source: string;
  timestamp: string;
  raw_message: string;
  model_used: string;
  classification: ClassificationResult;
  enrichment: EnrichmentResult;
  routing: RoutingResult;
  summary: string;
}

export interface StepEvent {
  step: number;
  name: string;
  status: "running" | "done" | "error";
  data?: Record<string, unknown> | null;
  error?: string | null;
}

export interface AvailableModels {
  available: Record<string, string[]>;
  default: string;
}
