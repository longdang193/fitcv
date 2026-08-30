export type RunBackendStatus =
  | "queued"
  | "running"
  | "awaiting_continue"
  | "cancelling"
  | "cancelled"
  | "succeeded"
  | "failed";

export type RunDisplayStatus = "Running" | "Succeeded" | "Failed" | string;

export type RunLifecycle = "active" | "archived" | "all";

export type RunStageId =
  | "enrichment"
  | "screening"
  | "shortlisting"
  | "ranking"
  | "cv-analysis"
  | "cv-generation";

export type RunStageStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "warning"
  | "partial"
  | "failed"
  | "cancelled"
  | "skipped";

export type JobStageStatus =
  | "pending"
  | "passed"
  | "rejected"
  | "blocked"
  | "skipped"
  | "failed"
  | "review_required"
  | "generated"
  | string;

export type ResultBucket = "passed" | "rejected" | null;

export interface RunCapabilities {
  inspect: boolean;
  cancel: boolean;
  archive: boolean;
  unarchive: boolean;
  delete: boolean;
  export: boolean;
}

export interface DebugBundleAvailability {
  run_id: string;
  status: "available" | "not_ready" | "unavailable";
  reason?: string | null;
  action?: string | null;
}

export interface RunCounts {
  total: number;
  passed: number;
  rejected: number;
  skipped: number;
  cvs_generated: number;
}

export interface RunProgress {
  completed: number;
  total: number;
}

export interface RunErrors {
  code?: string | null;
  message?: string | null;
}

export interface RunInputSource {
  type: "upload" | "scan";
  filename?: string;
  scan_id?: string;
  scan_name?: string;
  record_count?: number;
  sha256?: string;
  byte_length?: number;
}

export interface RunInputSummary {
  run_id?: string;
  jobs_input_source?: string;
  jobs_input_manifest_json?: string;
  candidate_profile_source?: string;
  candidate_profile_json?: string;
  run_mode?: string;
  config_path?: string;
  sources?: RunInputSource[];
  [key: string]: unknown;
}

export interface RunStageResource {
  stage_id: RunStageId;
  label: string;
  ordinal: number;
  status: RunStageStatus;
  warnings?: Record<string, unknown>;
  results_available?: boolean;
  recomputed_counts?: {
    passed: number;
    rejected: number;
  };
}

export interface IntegrityWarning {
  code: string;
  stored?: Record<string, unknown>;
  recomputed?: Record<string, unknown>;
}

export interface PipelineRunResource {
  run_id: string;
  run_name: string;
  backend_status: RunBackendStatus;
  display_status: RunDisplayStatus;
  status_detail?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  archived_at?: string | null;
  counts: RunCounts;
  progress: RunProgress;
  warnings?: Record<string, unknown>;
  errors?: RunErrors;
  partial_completion?: boolean;
  input?: RunInputSummary | null;
  stages?: RunStageResource[];
  capabilities: RunCapabilities;
  integrity_warnings?: IntegrityWarning[];
  debug_bundle?: DebugBundleAvailability;
  links?: Record<string, string>;
}

export interface RunJobItem {
  run_job_id: string;
  job_id: string;
  title: string;
  company: string;
  location?: string;
  current_stage_id: string;
  status: JobStageStatus;
  result_bucket: ResultBucket;
  bookmarked?: boolean;
  bookmark_id?: string | null;
  interest_rating?: number | null;
  cv_versions_count?: number;
  latest_cv_generation_status?: string | null;
  latest_cv_review_state?: string | null;
  attributes?: Record<string, unknown>;
  capabilities?: {
    bookmark?: boolean;
    interest?: boolean;
    cv_view?: boolean;
    cv_generate?: boolean;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface RunEventRecord {
  event_id: string;
  time: string;
  stage_id: string;
  level: "info" | "warning" | "error";
  operation: string;
  state: string;
  message: string;
  payload?: Record<string, unknown>;
  diagnostic_refs?: Record<string, unknown>;
}

export interface RunEventsPage {
  events: RunEventRecord[];
  next_cursor?: string | null;
  integrity_conflicts: number;
  total_count: number;
}

export interface DeleteArchivedRunsPreview {
  requested_run_ids: string[];
  matched_run_ids: string[];
  blocked_run_ids: string[];
  missing_run_ids: string[];
  state_tokens: string[];
  preview_revision: string;
}

export interface RunsPaginationMeta {
  active_count: number;
  archived_count: number;
  view: string;
  search: string;
  server_time: string;
}

export interface RunJobsPaginationMeta {
  run_id: string;
  stage: string;
  result_bucket: string;
  search: string;
  total_evaluated: number;
  passed: number;
  rejected: number;
  skipped: number;
}
