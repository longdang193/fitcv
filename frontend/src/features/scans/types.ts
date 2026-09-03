export type PublishedWindow =
  | "any"
  | "past_12_hours"
  | "past_24_hours"
  | "past_7_days"
  | "past_30_days"
  | "past_180_days";

export type ScanExecutionStatus =
  | "queued"
  | "running"
  | "cancelling"
  | "succeeded"
  | "failed"
  | "cancelled";

export type ScanLifecycle = "active" | "archived";

export interface ScanCapabilities {
  inspect: boolean;
  cancel: boolean;
  run_again: boolean;
  download: boolean;
  archive: boolean;
  unarchive: boolean;
  delete: boolean;
  use_for_run: boolean;
}

export interface TrackedCompanySnapshot {
  company_id: string;
  company_name: string;
  careers_url: string;
  provider_id: string;
  provider_label?: string | null;
}

export interface TrackedCompanyResource extends TrackedCompanySnapshot {
  row_revision: number;
  created_at: string;
  updated_at: string;
}

export interface ScanInputData {
  scan_name?: string | null;
  company_ids: string[];
  job_titles: string[];
  locations: string[];
  published_window: PublishedWindow;
  total_rows: number;
}

export interface ScanResource {
  scan_id: string;
  scan_name: string;
  execution_status: ScanExecutionStatus;
  lifecycle: ScanLifecycle;
  row_revision: number;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  company_count: number;
  output_record_count?: number | null;
  capabilities: ScanCapabilities;
  warnings: string[];
  failure_code?: string | null;
  failure_message?: string | null;
  input?: ScanInputData;
  company_snapshots?: TrackedCompanySnapshot[];
  output_integrity_valid?: boolean;
  output_sha256?: string | null;
  output_byte_length?: number | null;
}

export interface ProcessEventRecord {
  schema_version?: string;
  event_id: string;
  event_seq?: number;
  process_type: string;
  process_id: string;
  operation?: string;
  state?: string;
  stage_name?: string;
  event_type?: string;
  level?: "info" | "warning" | "error";
  event_level?: "info" | "warning" | "error";
  message?: string;
  payload?: Record<string, unknown>;
  payload_json?: string | null;
  diagnostic_refs_json?: string | null;
  trace_context_json?: string | null;
  recorded_at: string;
  event_fingerprint?: string;
}

export interface ProcessEventsPage {
  events: ProcessEventRecord[];
  next_cursor?: string | null;
  total_count?: number;
}

export interface ScanJobItem {
  id?: string;
  title: string;
  companyName?: string;
  jobUrl?: string;
  applyUrl?: string;
  publishedAt?: string | null;
  contractType?: string;
  experienceLevel?: string;
  description?: string;
  job_url?: string;
  company?: string;
  company_name?: string;
  location?: string;
  url?: string;
  posted_at?: string;
  posted_time?: string;
  published_at?: string | null;
  apply_url?: string;
  contract_type?: string;
  experience_level?: string;
  work_type?: string;
  sector?: string;
  salary?: string;
  applications_count?: string | number;
  [key: string]: unknown;
}

export interface ScanCreatePayload {
  scan_name?: string | null;
  company_ids: string[];
  job_titles?: string[];
  locations?: string[];
  published_window?: PublishedWindow;
  total_rows?: number;
}

export interface TrackedCompanyVerifyPayload {
  company_name: string;
  careers_url: string;
}

export interface TrackedCompanyCreatePayload extends TrackedCompanyVerifyPayload {}

export interface TrackedCompanyVerifyResult {
  company_name: string;
  careers_url: string;
  provider_id: string;
  provider_label: string;
}

export interface DeletePreviewResult {
  eligible_scan_ids: string[];
  referenced_scan_ids: string[];
  invalid_scan_ids: string[];
  missing_scan_ids: string[];
  preview_revision: string;
  row_revisions: Record<string, number>;
}
