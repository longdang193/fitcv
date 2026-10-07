export interface AnalyticsCoverage {
  status: "available" | "unavailable";
  sample_size: number;
  source_mix: string[];
  collection_window: { start: string | null; end: string | null };
  candidate_revisions: Array<Record<string, unknown>>;
  unavailable_reasons: string[];
  source_commit?: string;
}

export interface AnalyticsDashboardData {
  coverage: AnalyticsCoverage;
  metadata: Record<string, unknown>;
  opportunity_landscape: Array<Record<string, unknown>>;
  requirement_demand: Array<Record<string, unknown>>;
  candidate_evidence_gaps: Array<Record<string, unknown>>;
}

export interface AnalyticsTraceData {
  coverage: AnalyticsCoverage;
  posting: Record<string, unknown> | null;
  requirements: Array<Record<string, unknown>>;
  candidate_evidence_gaps: Array<Record<string, unknown>>;
}
