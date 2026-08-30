export interface BookmarkItem {
  bookmark_id: string;
  bookmarked_at: string;
  run_id: string;
  run_name?: string;
  run_job_id: string;
  title: string;
  company: string;
  location?: string;
  rating?: number | null;
  rating_contract_revision?: string | null;
  cv_version_id?: string | null;
  cv_generation_status?: string | null;
  cv_available?: number | boolean;
  stage_id?: string;
  status?: string;
  outcome_code?: string;
  reason_code?: string;
  result_bucket?: "passed" | "rejected" | null;
  skills?: string[];
  evidence?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface BookmarksPaginationEnvelope {
  data: BookmarkItem[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages?: number;
  meta?: Record<string, unknown>;
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
