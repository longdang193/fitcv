export type SynonymType = "skills" | "domain" | "role_family";
export type ReviewStatus = "pending" | "approved" | "declined";

export interface SynonymPolicyIssue {
  code: string;
  message: string;
  severity: "error" | "warning";
  lines: number[];
  aliases: string[];
  canonicals: string[];
}

export interface SynonymPolicyResource {
  synonym_type: SynonymType;
  editor_text: string;
  normalized_policy: Record<string, string> | null;
  issues: SynonymPolicyIssue[];
  validation_status: "valid" | "invalid";
  draft_revision: number;
  active_type_revision_id: string | null;
  active_type_revision: number;
  active_bundle_revision_id: string | null;
  active_bundle_revision: number;
  mirror_status: "in_sync" | "repair_required" | "repair_failed";
  mirror_error_code: string | null;
}

export interface SynonymPolicyEnvelope {
  data: SynonymPolicyResource;
}

export interface SynonymPolicyUpdateRequest {
  editor_text: string;
  expected_draft_revision: number;
  expected_active_bundle_revision_id: string | null;
}

export interface SynonymSuggestionSource {
  run_id: string;
  occurrence_count: number;
  first_seen_at?: string;
  last_seen_at?: string;
  run_name?: string;
  evidence_json?: string;
  evidence?: Record<string, any>;
}

export interface SynonymSuggestionResource {
  suggestion_id: string;
  synonym_type: SynonymType;
  alias: string;
  canonical: string;
  normalized_alias: string;
  normalized_canonical: string;
  review_status: ReviewStatus;
  confidence?: number | null;
  candidate_canonicals: string[];
  source_count: number;
  updated_at: string;
  created_at: string;
  sources?: SynonymSuggestionSource[];
  evidence_total?: number;
  evidence_page?: number;
  evidence_page_size?: number;
  [key: string]: any;
}

export interface SynonymCounts {
  skills: { pending: number; approved: number; declined: number; total: number };
  domain: { pending: number; approved: number; declined: number; total: number };
  role_family: { pending: number; approved: number; declined: number; total: number };
}

export interface CandidateProfilePage {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface SynonymSuggestionCollectionEnvelope {
  data: SynonymSuggestionResource[];
  page: CandidateProfilePage;
  meta: {
    counts?: Record<string, { pending?: number; approved?: number; declined?: number; total?: number }>;
    [key: string]: any;
  };
}

export interface SynonymSuggestionEnvelope {
  data: SynonymSuggestionResource;
}

export interface SynonymProcessingResource {
  processing_run_id: string;
  processed_at: string;
  total_processed: number;
  approved_count: number;
  declined_count: number;
  pending_count: number;
  successfully_added_count: number;
  source_operation: string;
  issue_count: number;
}

export interface SynonymProcessingCollectionEnvelope {
  data: SynonymProcessingResource[];
  page: CandidateProfilePage;
  meta: Record<string, any>;
}

export interface SynonymSuggestionQuery {
  type?: SynonymType | "all";
  status?: ReviewStatus | "all";
  search?: string;
  page?: number;
  pageSize?: 10 | 20 | 50;
  sort?: "updated_desc";
}

export interface SynonymActionResult {
  applied_count?: number;
  approved_count?: number;
  declined_count?: number;
  cleared_count?: number;
  action?: string;
  [key: string]: any;
}
