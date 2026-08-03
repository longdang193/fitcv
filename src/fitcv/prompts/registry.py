"""@meta
name: registry
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.prompts.registry.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

from __future__ import annotations

from pathlib import Path

from fitcv.prompts.models import PromptDefinition

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_PROMPT_REGISTRY: dict[str, PromptDefinition] = {
    "candidate_profile.base_mapping.v1": PromptDefinition(
        prompt_id="candidate_profile.base_mapping.v1",
        stage_id="candidate_profile_base_mapping",
        version="v1",
        template_path=_TEMPLATES_DIR / "candidate_profile_base_mapping_v1.md",
        summary="Evidence-bound baseline mapping for Candidate Profile creation.",
    ),
    "candidate_profile.derived_claims.v1": PromptDefinition(
        prompt_id="candidate_profile.derived_claims.v1",
        stage_id="candidate_profile_derived_claims",
        version="v1",
        template_path=_TEMPLATES_DIR / "candidate_profile_derived_claims_v1.md",
        summary="Evidence-bound controlled derivation for Candidate Profile creation.",
    ),
    "enrich.extraction.v1": PromptDefinition(
        prompt_id="enrich.extraction.v1",
        stage_id="enrich",
        version="v1",
        template_path=_TEMPLATES_DIR / "enrich_extraction_v1.md",
        summary="Structured JD extraction prompt for the enrich stage.",
    ),
    "ranking.ai_score.v1": PromptDefinition(
        prompt_id="ranking.ai_score.v1",
        stage_id="ranking",
        version="v1",
        template_path=_TEMPLATES_DIR / "ranking_ai_score_v1.md",
        summary="Structured AI reranking prompt for shortlist scoring.",
    ),
    "ranking.ai_score.v2": PromptDefinition(
        prompt_id="ranking.ai_score.v2",
        stage_id="ranking",
        version="v2",
        template_path=_TEMPLATES_DIR / "ranking_ai_score_v2.md",
        summary="Holistic AI fit-score prompt without label authority.",
    ),
    "cv_generation.write.v1": PromptDefinition(
        prompt_id="cv_generation.write.v1",
        stage_id="cv_generation",
        version="v1",
        template_path=_TEMPLATES_DIR / "cv_generation_write_v1.md",
        summary="Primary CV generation writer prompt for markdown CV output.",
    ),
    "cv_generation.structured_write.v1": PromptDefinition(
        prompt_id="cv_generation.structured_write.v1",
        stage_id="cv_generation",
        version="v1",
        template_path=_TEMPLATES_DIR / "cv_generation_structured_write_v1.md",
        summary="Primary CV generation writer prompt for structured JSON CV output.",
    ),
    "synonym_triage.recommendation.v1": PromptDefinition(
        prompt_id="synonym_triage.recommendation.v1",
        stage_id="synonym_triage",
        version="v1",
        template_path=_TEMPLATES_DIR / "synonym_triage_recommendation_v1.md",
        summary="Synonym triage recommendation prompt for control-plane provider routing.",
    ),
}


def get_prompt_definition(prompt_id: str) -> PromptDefinition:
    try:
        return _PROMPT_REGISTRY[prompt_id]
    except KeyError as exc:
        raise KeyError(f"Unknown prompt_id: {prompt_id}") from exc
