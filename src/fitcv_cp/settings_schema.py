"""Registry of admin-editable pipeline settings.

Each entry defines:
  key         Dotted name used in pipeline_settings BQ table and POST /runs overrides
  type        "int" or "float"
  default     YAML baseline default (for display purposes; source of truth is config/*.yaml)
  label       Human-readable display name shown in the admin UI
  group       UI section: "retrieval" | "timing" | "ranking"
  config_path List of keys to traverse when applying to a config dict
              e.g. ["pipeline", "final_top_n"] → config["pipeline"]["final_top_n"]

Validation rules are enforced by validate_settings().
"""
from __future__ import annotations

from typing import Any


class ValidationError(ValueError):
    pass


# ── schema registry ──────────────────────────────────────────────────────────

SETTINGS_SCHEMA: list[dict[str, Any]] = [
    # ── Retrieval ─────────────────────────────────────────────────────────────
    {
        "key": "pipeline.vector_search_top_n",
        "type": "int",
        "default": 50,
        "label": "Initial Candidate Pool Size",
        "description": "The number of candidates to retrieve from the vector database after applying deterministic rule filters.",
        "group": "retrieval",
        "config_path": ["pipeline", "vector_search_top_n"],
    },
    {
        "key": "pipeline.ai_score_top_n",
        "type": "int",
        "default": 50,
        "label": "AI Reranking Pool Size",
        "description": "The maximum number of shortlisted candidates to evaluate using the LLM for deep semantic scoring.",
        "group": "retrieval",
        "config_path": ["pipeline", "ai_score_top_n"],
    },
    {
        "key": "pipeline.final_top_n",
        "type": "int",
        "default": 10,
        "label": "Final Output Count",
        "description": "The target number of highly qualified candidates to include in the final CV generation.",
        "group": "retrieval",
        "config_path": ["pipeline", "final_top_n"],
    },
    {
        "key": "pipeline.evidence_top_k",
        "type": "int",
        "default": 5,
        "label": "Evidence Chunks Limit",
        "description": "The maximum number of resume experience chunks to retrieve when writing the justification for a candidate.",
        "group": "retrieval",
        "config_path": ["pipeline", "evidence_top_k"],
    },
    # ── Timing / Throttling ───────────────────────────────────────────────────
    {
        "key": "enrichment_sleep_secs",
        "type": "float",
        "default": 1.0,
        "label": "API Delay: Data Enrichment",
        "description": "Seconds to wait between calls to the web scraping/enrichment API to avoid rate limiting.",
        "group": "timing",
        "config_path": ["enrichment_sleep_secs"],
    },
    {
        "key": "rerank_sleep_secs",
        "type": "float",
        "default": 0.5,
        "label": "API Delay: AI Reranking",
        "description": "Seconds to wait between concurrent/sequential LLM calls during candidate scoring.",
        "group": "timing",
        "config_path": ["rerank_sleep_secs"],
    },
    {
        "key": "enrichment_batch_size",
        "type": "int",
        "default": 10,
        "label": "Enrichment Batch Size",
        "description": "How many jobs to enrich in one bounded worker batch.",
        "group": "timing",
        "config_path": ["enrichment_batch_size"],
    },
    {
        "key": "enrichment_concurrency",
        "type": "int",
        "default": 1,
        "label": "Enrichment Concurrency",
        "description": "How many enrichment batches may run concurrently. Default 1 (sequential). Higher values increase API throughput but risk provider rate-limit errors (429) because per-thread sleep is not a global rate limiter.",
        "group": "timing",
        "config_path": ["enrichment_concurrency"],
    },
    # ── Ranking Policy ────────────────────────────────────────────────────────
    {
        "key": "ranking_weights.ai_score",
        "type": "float",
        "default": 0.40,
        "label": "Weight: AI Score",
        "description": "How much influence the LLM-evaluated fit score has on the final candidate ranking.",
        "group": "ranking",
        "config_path": ["ranking_weights", "ai_score"],
    },
    {
        "key": "ranking_weights.must_have_match",
        "type": "float",
        "default": 0.20,
        "label": "Weight: Must-Have Skills",
        "description": "How much influence the strict matching of required skills has on the final ranking.",
        "group": "ranking",
        "config_path": ["ranking_weights", "must_have_match"],
    },
    {
        "key": "ranking_weights.vector_similarity",
        "type": "float",
        "default": 0.15,
        "label": "Weight: Vector Similarity",
        "description": "How much influence the embedding-based vector similarity score has on the final ranking.",
        "group": "ranking",
        "config_path": ["ranking_weights", "vector_similarity"],
    },
    {
        "key": "ranking_weights.title_relevance",
        "type": "float",
        "default": 0.10,
        "label": "Weight: Title Relevance",
        "description": "How much influence past job title similarity has on the final ranking.",
        "group": "ranking",
        "config_path": ["ranking_weights", "title_relevance"],
    },
    {
        "key": "ranking_weights.seniority_fit",
        "type": "float",
        "default": 0.10,
        "label": "Weight: Seniority Alignment",
        "description": "How much influence the match between job seniority requirements and candidate experience has.",
        "group": "ranking",
        "config_path": ["ranking_weights", "seniority_fit"],
    },
    {
        "key": "ranking_weights.preference_fit",
        "type": "float",
        "default": 0.05,
        "label": "Weight: Nice-to-Have Skills",
        "description": "How much influence preferred or optional skills have on the final candidate ranking.",
        "group": "ranking",
        "config_path": ["ranking_weights", "preference_fit"],
    },
    {
        "key": "fit_label_thresholds.strong",
        "type": "float",
        "default": 0.70,
        "label": "Threshold: Strong Overall Fit",
        "description": "The minimum combined score (0.0 to 1.0) required to categorize a candidate as a 'Strong' fit.",
        "group": "ranking",
        "config_path": ["fit_label_thresholds", "strong"],
    },
    {
        "key": "fit_label_thresholds.stretch",
        "type": "float",
        "default": 0.40,
        "label": "Threshold: Stretch Overall Fit",
        "description": "The minimum combined score (0.0 to 1.0) required to categorize a candidate as a 'Stretch' fit.",
        "group": "ranking",
        "config_path": ["fit_label_thresholds", "stretch"],
    },
    {
        "key": "gap_thresholds.strong_min_matched_ratio",
        "type": "float",
        "default": 0.80,
        "label": "Skill Ratio Limit: Strong Match",
        "description": "The minimum percentage of required skills a candidate must possess to avoid a 'Strong' gap penalty.",
        "group": "ranking",
        "config_path": ["gap_thresholds", "strong_min_matched_ratio"],
    },
    {
        "key": "gap_thresholds.stretch_min_matched_ratio",
        "type": "float",
        "default": 0.50,
        "label": "Skill Ratio Limit: Stretch Match",
        "description": "The minimum percentage of required skills a candidate must possess to avoid a 'Stretch' gap penalty.",
        "group": "ranking",
        "config_path": ["gap_thresholds", "stretch_min_matched_ratio"],
    },
    # ── Global Job Filters ──────────────────────────────────────────────────────────────────────
    {
        "key": "global_job_filters.applications_count_max",
        "type": "int",
        "default": 200,
        "label": "Maximum Applicant Count",
        "description": "Reject jobs when the applicant count exceeds this threshold.",
        "group": "global_job_filters",
        "config_path": ["global_job_filters", "applications_count_max"],
    },
    {
        "key": "global_job_filters.max_age_days",
        "type": "int",
        "default": 30,
        "label": "Maximum Posting Age (Days)",
        "description": "Reject jobs when the posting is older than this many days. Missing posted date is treated as passing.",
        "group": "global_job_filters",
        "config_path": ["global_job_filters", "max_age_days"],
    },
    # ── CV Generation ──────────────────────────────────────────────────────
    {
        "key": "cv_generation_model",
        "type": "str",
        "default": "gemini-2.5-flash",
        "label": "CV Generation Model",
        "description": "The LLM model used to generate candidate CV documents.",
        "group": "cv_composition",
        "config_path": ["cv", "generation", "model"],
    },
    {
        "key": "cv_prompt_version",
        "type": "str",
        "default": "v1",
        "label": "Prompt Version",
        "description": "Version identifier for the CV generation prompt used.",
        "group": "cv_composition",
        "config_path": ["cv", "generation", "prompt_version"],
    },
    {
        "key": "cv_template_path",
        "type": "str",
        "default": "templates/cv_template.md",
        "label": "CV Template Path",
        "description": "Path to the Jinja2 template used for CV generation.",
        "group": "cv_generation",
        "config_path": ["cv_template_path"],
    },
    {
        "key": "cv_preset",
        "type": "str",
        "default": "europass",
        "label": "CV Preset",
        "description": "The CV preset to use for generation. Controls template, section order, and supported composition options.",
        "group": "cv_preset",
        "config_path": ["cv", "preset"],
    },
    # ── CV Composition ─────────────────────────────────────────────────────────
    {
        "key": "cv_summary_style",
        "type": "str",
        "default": "concise",
        "label": "Summary Style",
        "description": "Style of the professional summary section in generated CVs.",
        "group": "cv_composition",
        "config_path": ["cv", "composition", "summary", "style"],
    },
    {
        "key": "cv_education_enabled",
        "type": "bool",
        "default": True,
        "label": "Include Education",
        "description": "Whether to include an Education section in generated CVs.",
        "group": "cv_composition",
        "config_path": ["cv", "composition", "education", "enabled"],
    },
    {
        "key": "cv_education_detail",
        "type": "str",
        "default": "compact",
        "label": "Education Detail Level",
        "description": "How much detail to include in the Education section: compact, standard, or detailed.",
        "group": "cv_composition",
        "config_path": ["cv", "composition", "education", "detail"],
    },
    {
        "key": "cv_experience_enabled",
        "type": "bool",
        "default": True,
        "label": "Include Experience",
        "description": "Whether to include a Work Experience section in generated CVs.",
        "group": "cv_composition",
        "config_path": ["cv", "composition", "experience", "enabled"],
    },
    {
        "key": "cv_experience_bullet_style",
        "type": "str",
        "default": "action_project_result",
        "label": "Experience Bullet Style",
        "description": "Style of bullet points in work experience entries.",
        "group": "cv_composition",
        "config_path": ["cv", "composition", "experience", "bullet_style"],
    },
    {
        "key": "cv_skills_enabled",
        "type": "bool",
        "default": True,
        "label": "Include Skills",
        "description": "Whether to include a Skills section in generated CVs.",
        "group": "cv_composition",
        "config_path": ["cv", "composition", "skills", "enabled"],
    },
    {
        "key": "cv_skills_max_items",
        "type": "int",
        "default": 12,
        "label": "Skills Max Items",
        "description": "Maximum number of skills to include in the Skills section.",
        "group": "cv_composition",
        "config_path": ["cv", "composition", "skills", "max_items"],
    },
    {
        "key": "cv_certifications_enabled",
        "type": "bool",
        "default": True,
        "label": "Include Certifications",
        "description": "Whether to include a Certifications section in generated CVs.",
        "group": "cv_composition",
        "config_path": ["cv", "composition", "certifications", "enabled"],
    },
    {
        "key": "cv_projects_enabled",
        "type": "bool",
        "default": True,
        "label": "Include Projects",
        "description": "Whether to include a Projects section in generated CVs.",
        "group": "cv_composition",
        "config_path": ["cv", "composition", "projects", "enabled"],
    },
    {
        "key": "cv_projects_required",
        "type": "bool",
        "default": True,
        "label": "Projects Required",
        "description": "Whether the Projects section is required (vs optional) in generated CVs.",
        "group": "cv_composition",
        "config_path": ["cv", "composition", "projects", "required"],
    },
    # ── CV Content Rules ──────────────────────────────────────────────────────
    {
        "key": "cv_emphasize_required_skills",
        "type": "bool",
        "default": True,
        "label": "Emphasize Required Skills",
        "description": "When enabled, required skills from the job description are prominently featured in the CV.",
        "group": "cv_content_rules",
        "config_path": ["cv", "content_rules", "emphasize_required_skills"],
    },
    {
        "key": "cv_align_jd_terminology",
        "type": "bool",
        "default": True,
        "label": "Align JD Terminology",
        "description": "When enabled, the CV uses terminology matching the job description.",
        "group": "cv_content_rules",
        "config_path": ["cv", "content_rules", "align_jd_terminology"],
    },
    {
        "key": "cv_evidence_grounded_only",
        "type": "bool",
        "default": True,
        "label": "Evidence Grounded Only",
        "description": "When enabled, only claims with evidence from the candidate profile are included in the CV.",
        "group": "cv_content_rules",
        "config_path": ["cv", "content_rules", "evidence_grounded_only"],
    },
    # ── CV Validation ────────────────────────────────────────────────────────
    {
        "key": "cv_max_pages",
        "type": "int",
        "default": 2,
        "label": "CV Maximum Pages",
        "description": "The maximum number of pages for a generated CV document.",
        "group": "cv_validation",
        "config_path": ["cv", "validation", "max_pages"],
    },
]

# ── Ranking group registry ────────────────────────────────────────────────────
# Maps URL group slug → ordered list of schema keys in that group.
# Used by the grouped-edit endpoint and the settings template.

RANKING_GROUPS: dict[str, list[str]] = {
    "ranking-weights": [
        "ranking_weights.ai_score",
        "ranking_weights.must_have_match",
        "ranking_weights.vector_similarity",
        "ranking_weights.title_relevance",
        "ranking_weights.seniority_fit",
        "ranking_weights.preference_fit",
    ],
    "fit-label-thresholds": [
        "fit_label_thresholds.strong",
        "fit_label_thresholds.stretch",
    ],
    "gap-thresholds": [
        "gap_thresholds.strong_min_matched_ratio",
        "gap_thresholds.stretch_min_matched_ratio",
    ],
}

# ── Independent settings section registry ─────────────────────────────────────
# Maps URL section slug → ordered list of schema keys in that section.
# Used by the section-save endpoint (/admin/settings/section/{name}).
# Each section uses one form with one save action; keys are validated
# individually (no cross-key constraints within a section).

SETTINGS_SECTIONS: dict[str, list[str]] = {
    "retrieval": [
        "pipeline.vector_search_top_n",
        "pipeline.ai_score_top_n",
        "pipeline.final_top_n",
        "pipeline.evidence_top_k",
    ],
    "timing": [
        "enrichment_sleep_secs",
        "rerank_sleep_secs",
        "enrichment_batch_size",
        "enrichment_concurrency",
    ],
    "global-job-filters": [
        "global_job_filters.applications_count_max",
        "global_job_filters.max_age_days",
    ],
}

# ── CV Generation settings schema ──────────────────────────────────────────
# Kept for reference and documentation only.  The actual schema entries live
# inside SETTINGS_SCHEMA so they appear alongside all other settings.
# _CV_GENERATION_SCHEMA was removed to avoid duplication.

# ── CV group registry ───────────────────────────────────────────────────────
# Maps URL group slug (used in /admin/settings/group/{slug}) → ordered list
# of schema keys.  CV groups are validated and saved together, just like
# ranking groups, but are kept in a separate namespace.
CV_GROUPS: dict[str, list[str]] = {
    "cv-preset": [
        "cv_preset",
        "cv_generation_model",
        "cv_prompt_version",
    ],
    "cv-composition": [
        "cv_summary_style",
        "cv_education_enabled",
        "cv_education_detail",
        "cv_experience_enabled",
        "cv_experience_bullet_style",
        "cv_skills_enabled",
        "cv_skills_max_items",
        "cv_certifications_enabled",
        "cv_projects_enabled",
        "cv_projects_required",
    ],
    "cv-content-rules": [
        "cv_emphasize_required_skills",
        "cv_align_jd_terminology",
        "cv_evidence_grounded_only",
    ],
    "cv-validation": [
        "cv_max_pages",
    ],
}

# ── Combined grouped-registry lookup ───────────────────────────────────────
# Used by the grouped-save endpoint to validate any group request.
ALL_GROUP_REGISTRIES: dict[str, dict[str, list[str]]] = {
    "ranking": RANKING_GROUPS,
    "cv": CV_GROUPS,
}

# Build lookup maps once
_ALL_SCHEMA_BY_KEY: dict[str, dict[str, Any]] = {s["key"]: s for s in SETTINGS_SCHEMA}
_WEIGHT_KEYS: frozenset[str] = frozenset(
    s["key"] for s in SETTINGS_SCHEMA if s["key"].startswith("ranking_weights.")
)


# ── coercion ──────────────────────────────────────────────────────────────────

def coerce_value(key: str, raw: Any) -> int | float | str | bool | list[str]:
    """Cast raw value (string or numeric) to the type declared in the schema."""
    entry = _ALL_SCHEMA_BY_KEY[key]  # raises KeyError for unknown keys
    if entry["type"] == "int":
        return int(raw)
    elif entry["type"] == "float":
        return float(raw)
    elif entry["type"] == "str":
        return str(raw).strip()
    elif entry["type"] == "bool":
        if isinstance(raw, bool):
            return raw
        s = str(raw).strip().lower()
        if s in ("true", "1", "yes", "on"):
            return True
        if s in ("false", "0", "no", "off", ""):
            return False
        raise ValueError(f"{key} must be a boolean value, got {raw!r}")
    elif entry["type"] == "list[str]":
        if isinstance(raw, list):
            return [str(v).strip() for v in raw]
        return [str(raw).strip()]
    raise TypeError(f"Unsupported type {entry['type']!r} for key {key!r}")


# ── validation ────────────────────────────────────────────────────────────────

def validate_settings(settings: dict[str, Any]) -> None:
    """Validate a (possibly partial) settings dict.

    Raises ValidationError with a descriptive message on any violation.
    settings values must already be coerced to their declared Python types.
    """
    for key, value in settings.items():
        if key not in _ALL_SCHEMA_BY_KEY:
            raise ValidationError(f"Unknown setting key: '{key}'")
        entry = _ALL_SCHEMA_BY_KEY[key]

        if entry["type"] == "int":
            if not isinstance(value, int) or value < 1:
                raise ValidationError(f"{key} must be an integer >= 1, got {value!r}")
        elif entry["type"] == "float":
            fval = float(value)
            if key.endswith("_secs"):
                if fval < 0.0:
                    raise ValidationError(f"{key} must be >= 0.0, got {fval}")
            else:
                if not (0.0 <= fval <= 1.0):
                    raise ValidationError(
                        f"{key} must be in range [0.0, 1.0], got {fval}"
                    )
        elif entry["type"] == "str":
            if not value or not value.strip():
                raise ValidationError(f"{key} must not be empty or whitespace-only")
        elif entry["type"] == "bool":
            if not isinstance(value, bool):
                raise ValidationError(f"{key} must be a boolean, got {value!r}")
        elif entry["type"] == "list[str]":
            if not isinstance(value, list):
                raise ValidationError(f"{key} must be a list of strings, got {type(value).__name__}")
            if len(value) == 0:
                raise ValidationError(f"{key} must not be empty")
            for item in value:
                if not isinstance(item, str) or not item.strip():
                    raise ValidationError(f"{key} contains a blank entry: {value!r}")
            seen: list[str] = []
            for item in value:
                if item in seen:
                    raise ValidationError(
                        f"{key} contains duplicate entries (order preserved, duplicates rejected): {value!r}"
                    )
                seen.append(item)

    # ── relational constraints ────────────────────────────────────────────────
    vs = settings.get("pipeline.vector_search_top_n")
    ai = settings.get("pipeline.ai_score_top_n")
    fn = settings.get("pipeline.final_top_n")
    if all(v is not None for v in [vs, ai]) and ai > vs:
        raise ValidationError(
            f"pipeline.ai_score_top_n ({ai}) must be <= pipeline.vector_search_top_n ({vs})"
        )
    if all(v is not None for v in [ai, fn]) and fn > ai:
        raise ValidationError(
            f"pipeline.final_top_n ({fn}) must be <= pipeline.ai_score_top_n ({ai})"
        )

    strong = settings.get("fit_label_thresholds.strong")
    stretch = settings.get("fit_label_thresholds.stretch")
    if strong is not None and stretch is not None and strong <= stretch:
        raise ValidationError(
            f"fit_label_thresholds.strong ({strong}) must be > stretch ({stretch})"
        )

    g_strong = settings.get("gap_thresholds.strong_min_matched_ratio")
    g_stretch = settings.get("gap_thresholds.stretch_min_matched_ratio")
    if g_strong is not None and g_stretch is not None and g_strong <= g_stretch:
        raise ValidationError(
            f"gap_thresholds.strong_min_matched_ratio ({g_strong}) must be > stretch ({g_stretch})"
        )

    # Ranking weights sum-to-1 only checked when all 6 are present
    if _WEIGHT_KEYS <= set(settings.keys()):
        total = sum(float(settings[k]) for k in _WEIGHT_KEYS)
        if abs(total - 1.0) > 0.01:
            raise ValidationError(
                f"ranking_weights must sum to 1.0 (± 0.01), got {total:.4f}"
            )


# ── config application ────────────────────────────────────────────────────────

def apply_settings_to_config(config: dict[str, Any], settings: dict[str, Any]) -> None:
    """Write settings values into a config dict in-place.

    Uses config_path from the schema registry to navigate nested dicts.
    settings values must already be coerced to their declared Python types.
    """
    for key, value in settings.items():
        path = _ALL_SCHEMA_BY_KEY[key]["config_path"]
        target = config
        for part in path[:-1]:
            target = target.setdefault(part, {})
        target[path[-1]] = value
