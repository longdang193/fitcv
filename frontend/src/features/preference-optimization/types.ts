export type RankingMode = "baseline" | "personalized";

export interface PersonalizationBounds {
  minimum: number;
  maximum: number;
  step: number;
}

export interface PersonalizationResource {
  ranking_mode: RankingMode;
  effective_ranking_mode: RankingMode;
  personalization_strength: number;
  baseline_fallback: boolean;
  active_policy_id: string | null;
  revision: string;
  bounds: PersonalizationBounds;
  [key: string]: unknown;
}

export interface PersonalizationPatchPayload {
  ranking_mode: RankingMode;
  personalization_strength?: number | null;
  expected_revision: string;
  updated_by?: string;
}

export interface PersonalizationCandidateSummary {
  policy_snapshot_id: string;
  domain_id: string;
  status: string;
  parent_policy_ref?: string;
  created_at?: string;
  event_watermark?: number;
}

export interface RatingEvidenceApiRow {
  run_id: string;
  alternative_id: string;
  source_job_url?: string;
  displayed_rank: number;
  baseline_fit: number;
  baseline_fit_label?: string;
  rating: number;
  rated_at: string;
  job_label?: string;
}

export interface PersonalizationOptimizationResource {
  domain_id: string;
  ranking_mode: RankingMode;
  effective_ranking_mode: RankingMode;
  personalization_strength: number;
  baseline_fallback: boolean;
  active_policy_id: string | null;
  settings_revision: string;
  evidence_head_fingerprint: string;
  evidence_ready: boolean;
  episode_count: number;
  rating_event_count: number;
  rating_evidence?: RatingEvidenceApiRow[];
  current_parent_ref: string;
  latest_candidate: PersonalizationCandidateSummary | null;
  candidate_activation_eligible: boolean;
  status: string | null;
  error_code: string | null;
  message: string | null;
  policy_snapshot_id?: string | null;
  preference_optimization_run_id?: string | null;
}

export interface PersonalizationCandidatePayload {
  expected_evidence_head_fingerprint: string;
  expected_parent_ref: string;
}

export interface PersonalizationCandidateActivationPayload
  extends PersonalizationCandidatePayload {
  actor: string;
}

export interface RatingEvidenceRow {
  ratedAt: number | string;
  runId: string;
  job: string;
  jobUrl?: string;
  savedRank: number;
  baselineFit: number;
  rating: number;
}

export interface OptimizationRunItem {
  id: string;
  policyVersionId?: string | null;
  createdAt: number | string;
  startedAt?: number | string;
  completedAt?: number | string;
  strength: number;
  status: string;
  comparisons?: number;
  usage?: string;
  runtimeCompatible?: boolean;
  hiddenAt?: number | null;
  coverage?: number | null;
  stability?: number | null;
  rejectionReason?: string;
  evidence?: RatingEvidenceRow[];
  logs?: Array<{
    recordedAt: number;
    level: string;
    operation: string;
    message: string;
  }>;
}
