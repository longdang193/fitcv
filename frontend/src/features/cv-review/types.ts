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
  is_current?: boolean | number;
  created_at?: string;
  [key: string]: unknown;
}

export interface CvCapabilities {
  download: boolean;
  preview: boolean;
  regenerate: boolean;
}

export interface CvVersionResource {
  version_id: string;
  run_id: string;
  run_job_id: string;
  job_url: string;
  ordinal: number;
  generation_status: "generated" | "review_required" | "pending" | "running" | "generation_failed" | string;
  content_checksum?: string | null;
  content_length?: number | null;
  media_type?: string | null;
  filename?: string | null;
  parent_cv_version_id?: string | null;
  created_at: string;
  error_code?: string | null;
  error_message?: string | null;
  cv_structured?: Record<string, unknown> | null;
  evaluation?: CvEvaluationData | null;
  review_state: string;
  capabilities: CvCapabilities;
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
