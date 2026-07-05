export interface ChangeIntelligenceTiming {
  intent_ms?: number;
  evidence_ms?: number;
  reasoning_ms?: number;
  report_ms?: number;
  total_ms?: number;
}

export interface EngineeringReport {
  title?: string;
  intent?: string;
  hero?: Record<string, unknown>;
  sections?: unknown[];
  generated_at?: string;
  [key: string]: unknown;
}

export interface ChangeIntelligenceResponse {
  report: EngineeringReport;
  timing?: ChangeIntelligenceTiming;
  generated_at?: string;
}
