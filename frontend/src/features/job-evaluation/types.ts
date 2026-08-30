export interface FitFactorResult {
  factor?: string;
  status?: string;
  passed?: boolean;
  score?: number;
  reason?: string;
  evidence?: string;
  [key: string]: unknown;
}

export interface JobFitEvidence {
  run_job_id: string;
  job_url?: string;
  source_job_url?: string;
  passed: boolean;
  reasons: string[];
  marks?: string[];
  fit_factor_results?: Record<string, FitFactorResult | unknown>;
  eligibility_decision?: string;
  eligibility_reason_codes?: string[];
  filtered_at?: string;
  [key: string]: unknown;
}

export interface SelectionContextPayload {
  selected_run_job_ids: string[];
  stage?: string;
  result?: string;
  search?: string;
}

export interface SelectionPreviewResponse {
  selected_count: number;
  matched_count: number;
  excluded_count: number;
  matched_run_job_ids: string[];
  excluded_run_job_ids: string[];
  preview_revision: string;
  expires_in_seconds: number;
  expires_at: string;
}

export interface SelectionExportPayload extends SelectionContextPayload {
  preview_revision: string;
}

export interface InterestUpdateResult {
  run_job_id: string;
  rating?: number | null;
  rating_contract_revision?: string;
  action_id?: string;
  [key: string]: unknown;
}

export interface BookmarkUpdateResult {
  run_job_id: string;
  bookmarked: boolean;
  bookmark_id?: string | null;
  [key: string]: unknown;
}
