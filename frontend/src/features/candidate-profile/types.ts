export interface CandidateProfileReviewOperation {
  operation: "add" | "replace" | "remove";
  path: string;
  value?: unknown;
}

export interface ReviewAnnotation {
  source_block_ids?: string[];
  regenerable?: boolean;
  origin?: string;
  confidence?: number;
}

export interface ReviewResource {
  attempt_id: string;
  stage: "baseline" | "derived";
  revision: number;
  fingerprint: string;
  document: Record<string, any>;
  annotations: Record<string, ReviewAnnotation>;
  validation: {
    valid: boolean;
    errors: string[];
    details?: Record<string, any>;
  };
  capabilities: {
    patch?: boolean;
    regenerate_all?: boolean;
    undo_regeneration?: boolean;
    approve?: boolean;
  };
}

export interface CreationAttempt {
  attempt_id: string;
  profile_name: string;
  creation_status:
    | "queued"
    | "extracting_base"
    | "base_mapping"
    | "base_review"
    | "deriving"
    | "derived_claims"
    | "derived_review"
    | "ready_to_confirm"
    | "confirmed"
    | "succeeded"
    | "failed"
    | string;
  revision: number;
  next_action: "review_baseline" | "review_derived" | "confirm" | "view_profile" | "wait" | "none" | string;
  poll_after_ms?: number;
  source_format?: string;
  source_document?: {
    original_filename?: string;
    filename?: string;
    media_type?: string;
    byte_length?: number;
    checksum?: string;
  };
  fingerprints?: {
    baseline?: string;
    approved_baseline?: string;
    derived?: string;
    approved_derived?: string;
    confirmation?: string;
  };
  approval_timestamps?: {
    baseline?: string;
    derived?: string;
  };
  failure?: {
    code?: string;
    message?: string;
    retryable?: boolean;
  };
  capabilities: {
    retry?: boolean;
    cancel?: boolean;
    discard?: boolean;
  };
  profile_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ConfirmationResource {
  attempt_id: string;
  profile_name: string;
  revision: number;
  fingerprint: string;
  approval_fingerprints: {
    baseline?: string;
    derived?: string;
  };
  profile: {
    schema_version: string;
    canonical: Record<string, any>;
  };
  readiness: {
    ready: boolean;
    errors?: string[];
  };
  capabilities?: {
    confirm?: boolean;
  };
}

export interface SourceBlock {
  source_block_id: string;
  text: string;
  locator: {
    kind?: string;
    start?: number;
    end?: number;
    paragraph?: number;
    [key: string]: unknown;
  };
}

export interface ProfileCapabilities {
  archive?: boolean;
  restore?: boolean;
  delete?: boolean;
  use_for_run?: boolean;
  edit?: boolean;
}

export interface CandidateProfile {
  profile_id: string;
  profile_name: string;
  display_name: string;
  lifecycle: "active" | "archived";
  creation_status: string;
  revision: number;
  original_filename?: string;
  created_at: string;
  created_at_display?: string;
  capabilities: ProfileCapabilities;
  creation?: {
    attempt_id?: string;
    source_format?: string;
    method?: string;
  };
  failure?: {
    code?: string;
    message?: string;
  };
}

export interface CandidateProfileDetail extends CandidateProfile {
  canonical?: Record<string, any>;
  related_runs?: Array<{
    run_id: string;
    created_at?: string;
    status?: string;
  }>;
}

export interface FieldMeta {
  shape:
    | "text"
    | "textarea"
    | "select"
    | "month"
    | "month_or_present"
    | "number"
    | "status"
    | "collection"
    | "evidence_refs"
    | "source_refs";
  label: string;
  description?: string;
  required?: boolean;
  regenerable?: boolean;
  options?: Array<string | { value: string; label: string }>;
  item?: Record<string, FieldMeta>;
}

export interface SectionMeta {
  id: string;
  stage: "baseline" | "derived";
  shape: "object" | "collection" | "string_list";
  label: string;
  item_label?: string;
  description?: string;
  fields?: Record<string, FieldMeta>;
  item?: Record<string, FieldMeta>;
  required_one_of?: string[];
}

export interface FieldSchema {
  schema_version: string;
  schema_revision: number;
  checksum: string;
  date_grammar: {
    format: string;
    present_value: string;
    optional: boolean;
  };
  evidence_kinds: string[];
  sections: SectionMeta[];
}

export interface StoredReconciliation {
  attemptId: string;
  stage: "baseline" | "derived";
  revision: number;
  operations: CandidateProfileReviewOperation[];
  timestamp: number;
}
