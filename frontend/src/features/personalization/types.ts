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
