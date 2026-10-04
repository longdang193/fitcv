export interface CvEvaluationData {
  cv_evaluation_id?: string;
  cv_version_id?: string;
  run_job_id?: string;
  fit_classification?: string;
  scores?: Record<string, number | unknown>;
  strengths?: string[];
  weaknesses?: string[];
  recommendation?: string;
  evaluator_id?: string;
  notes?: string;
  is_current?: boolean | number;
  created_at?: string;
  [key: string]: unknown;
}

export interface CvCapabilities {
  download: boolean;
  preview: boolean;
  regenerate: boolean;
}

export interface CvQualityWarningsEnvelope {
  contract_version?: string;
  artifact_version_id?: string;
  content_checksum?: string | null;
  evidence_state?: "passed" | "failed" | "missing" | string;
  outcome?: "passed" | "warning" | "failure" | "missing" | string;
  warnings?: string[];
  page_count?: number | null;
  page_fit_status?: string | null;
  render_acceptance?: Record<string, unknown> | null;
  artifact_checksum?: string | null;
  render_proof?: Record<string, unknown> | null;
  run_id?: string | null;
  run_job_id?: string | null;
}

export type CvLifecycleStatus =
  | "pending"
  | "running"
  | "generated"
  | "review_required"
  | "rejected"
  | "cancelled"
  | "failed"
  | "generation_failed"
  | "validation_failed"
  | "persistence_failed"
  | string;

export interface CvReviewUncertainty {
  uncertainty_id?: string;
  resolution_key?: string;
  requirement_instance_id?: string;
  affected_fact?: string | null;
  question?: string | null;
  recommended_disposition?: string | null;
  qualifier?: string;
  message?: string;
  resolution_action?: CvReviewAction | string | null;
  resolution_status?: string | null;
  [key: string]: unknown;
}

export interface CvReviewResource {
  run_id: string;
  run_job_id: string;
  job_url?: string;
  cv_version_id?: string | null;
  status: CvLifecycleStatus;
  review_item_id?: string | null;
  reason_code?: string | null;
  uncertainties: CvReviewUncertainty[];
  resolution_key?: string | null;
  allowed_actions: CvReviewAction[];
  resolution_status?: string | null;
  final_artifact_evidence?: CvQualityWarningsEnvelope | null;
  cv_version?: CvVersionResource | null;
  refresh_required?: boolean;
}

export type CvReviewAction = "RESOLVE_WITH_ANSWER" | "CONFIRM_OMIT" | "OVERRIDE_BLOCK";

export interface CvReviewActionRequest {
  review_item_id?: string | null;
  uncertainty_id?: string | null;
  resolution_key?: string | null;
  action: CvReviewAction;
  actor?: string;
  note?: string | null;
  answer_text?: string | null;
}

export interface CvVersionResource {
  version_id: string;
  run_id: string;
  run_job_id: string;
  job_url: string;
  ordinal: number;
  generation_status: "generated" | "review_required" | "pending" | "running" | "generation_failed" | string;
  outcome_status?: "generated" | "review_required" | "pending" | "failed" | "missing" | string;
  evidence_state?: "passed" | "failed" | "missing" | string;
  content_checksum?: string | null;
  content_length?: number | null;
  media_type?: string | null;
  filename?: string | null;
  parent_cv_version_id?: string | null;
  created_at: string;
  error_code?: string | null;
  failure_code?: string | null;
  error_message?: string | null;
  cv_structured?: Record<string, unknown> | null;
  evaluation?: CvEvaluationData | null;
  review_state: string;
  quality_warnings?: CvQualityWarningsEnvelope | null;
  capabilities: CvCapabilities;
  etag?: string | null;
  [key: string]: unknown;
}

export interface CvPreviewResult {
  version_id: string;
  content: string;
  media_type: string;
  checksum: string;
  content_length: number;
}
export interface CvRegenerateRequest {
  parent_cv_version_id?: string | null;
}

export interface CvRegenerateResponseData {
  action_id: string;
  status: "queued" | "failed" | string;
  queue_job_id?: string | null;
  cv_version?: CvVersionResource;
}
