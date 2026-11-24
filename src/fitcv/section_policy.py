"""@meta
name: section_policy
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Shared Certifications section-policy helpers for generator/validator symmetry.
inputs:
  - CV configuration
  - Candidate profile certifications
  - Evidence-selected certifications
outputs:
  - Policy decision objects and formatted certification evidence lines
lifecycle:
  - status: active
"""

from __future__ import annotations

from typing import Any

from fitcv.config import CV_SECTION_KEY_TO_NAME

MYCVS_V1_SECTION_ORDER = (
    "header",
    "summary",
    "education",
    "experience",
    "projects",
    "certifications",
    "skills",
)

MYCVS_V1_SECTION_PRIORITY = {
    "header": 0,
    "summary": 1,
    "education": 2,
    "experience": 3,
    "projects": 4,
    "certifications": 5,
    "skills": 6,
}

MYCVS_V1_SECTION_BUDGET = {
    "summary": {"min_sentences": 2, "max_sentences": 4},
    "education": {"min_records": 0, "max_records": None},
    "experience": {"min_bullets": 3, "max_bullets": 5},
    "projects": {"min_bullets": 2, "max_bullets": 4},
    "certifications": {"min_records": 0, "max_records": None},
    "skills": {"min_tokens": 0, "max_tokens": None},
}

# This matrix is the myCVs source-of-truth contract. It deliberately does not
# reuse Europass' enabled/required-section semantics.
MYCVS_V1_SECTION_MATRIX = {
    "header": {
        "source_of_truth": "canonical_profile",
        "tailoring": "none",
        "presence": "mandatory",
        "validation": "canonical_name_and_optional_contact_fields",
    },
    "summary": {
        "source_of_truth": "canonical_profile_and_selected_job_support",
        "tailoring": "job_description",
        "presence": "mandatory",
        "validation": "2_to_4_grounded_sentences",
    },
    "education": {
        "source_of_truth": "canonical_profile",
        "tailoring": "relevant_optional_details",
        "presence": "source_driven",
        "validation": "definition_list_records",
    },
    "experience": {
        "source_of_truth": "canonical_profile_and_selected_job_support",
        "tailoring": "selected_support_controls_emphasis",
        "presence": "source_driven",
        "validation": "overview_plus_3_to_5_achievements",
    },
    "projects": {
        "source_of_truth": "canonical_profile_and_selected_job_support",
        "tailoring": "relevant_projects_first",
        "presence": "source_driven",
        "validation": "overview_plus_2_to_4_achievements_and_links",
    },
    "certifications": {
        "source_of_truth": "canonical_profile",
        "tailoring": "selected_support_is_context_only",
        "presence": "source_driven",
        "validation": "canonical_records_not_suppressed_or_truncated",
    },
    "skills": {
        "source_of_truth": "canonical_profile_and_selected_job_support",
        "tailoring": "normalize_dedupe_and_prioritize_against_jd",
        "presence": "source_driven",
        "validation": "grounded_canonical_tokens_not_selected_only",
    },
}

def resolve_mycvs_v1_policy(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the deterministic source-driven policy for the myCVs renderer."""
    # Legacy enabled/display settings remain for Europass, but cannot suppress
    # canonical myCVs records or change myCVs section presence.
    section_policy = {
        section: dict(MYCVS_V1_SECTION_MATRIX[section])
        for section in MYCVS_V1_SECTION_ORDER
    }
    composition = ((config or {}).get("cv") or {}).get("composition") or {}
    certification_config = composition.get("certifications") if isinstance(composition, dict) else None
    diagnostics: list[str] = []
    if isinstance(certification_config, dict):
        if "enabled" in certification_config:
            diagnostics.append("mycvs_v1 ignores cv.composition.certifications.enabled; presence is source-driven")
        if "max_items" in certification_config:
            diagnostics.append("mycvs_v1 ignores cv.composition.certifications.max_items; canonical certifications are not truncated")
        if "display_mode" in certification_config:
            diagnostics.append("mycvs_v1 ignores cv.composition.certifications.display_mode; certifications remain a separate source-driven section")
    return {
        "version": "mycvs_v1_section_policy_v1",
        "section_order": list(MYCVS_V1_SECTION_ORDER),
        "section_policy": section_policy,
        "section_priority": dict(MYCVS_V1_SECTION_PRIORITY),
        "section_budget": {key: dict(value) for key, value in MYCVS_V1_SECTION_BUDGET.items()},
        "legacy_setting_diagnostics": diagnostics,
    }


def _normalize_placeholder_token(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    normalized = normalized.replace("–", "-").replace("—", "-")
    return " ".join(normalized.split())


def _is_placeholder_token(value: Any) -> bool:
    return _normalize_placeholder_token(value) in {
        "",
        "n/a",
        "na",
        "none",
        "null",
        "tbd",
        "to be determined",
        "placeholder",
        "sample",
        "example",
        "your certification",
        "certification name",
        "issuer",
        "year",
        "yyyy",
    }


def _section_enabled(config: dict[str, Any], section_key: str) -> bool:
    composition = ((config.get("cv") or {}).get("composition") or {})
    section_cfg = composition.get(section_key)
    if not isinstance(section_cfg, dict):
        return True
    return bool(section_cfg.get("enabled", True))


def certification_rows_from_profile(profile: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows = profile.get("certifications") if isinstance(profile, dict) else []
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def is_meaningful_certification_row(row: dict[str, Any]) -> bool:
    name = str(row.get("name") or "").strip()
    issuer = str(row.get("issuer") or "").strip()
    year = row.get("year")
    if name and not _is_placeholder_token(name):
        return True
    if issuer and not _is_placeholder_token(issuer):
        return True
    if year and not _is_placeholder_token(year):
        return True
    return False


def meaningful_certification_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if is_meaningful_certification_row(row)]


def certification_policy_decisions(
    *,
    config: dict[str, Any],
    profile: dict[str, Any] | None,
    evidence_selected_certifications: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    section_key = "certifications"
    section_name = CV_SECTION_KEY_TO_NAME.get(section_key, "Certifications")
    enabled = _section_enabled(config, section_key)

    profile_rows = certification_rows_from_profile(profile)
    meaningful_profile_rows = meaningful_certification_rows(profile_rows)

    evidence_rows = [row for row in (evidence_selected_certifications or []) if isinstance(row, dict)]
    meaningful_evidence_rows = meaningful_certification_rows(evidence_rows)

    # Certifications are canonical profile records, not selected-evidence claims.
    # Keep evidence rows for tailoring/audit, but never use them as a gate.
    admissible_rows = meaningful_profile_rows
    admissible_via = "profile" if meaningful_profile_rows else "none"

    required = bool(admissible_rows)

    return {
        "section_key": section_key,
        "section_name": section_name,
        "enabled": enabled,
        "profile_rows": profile_rows,
        "meaningful_profile_rows": meaningful_profile_rows,
        "evidence_rows": evidence_rows,
        "meaningful_evidence_rows": meaningful_evidence_rows,
        "admissible_rows": admissible_rows,
        "admissible_via": admissible_via,
        "required": required,
    }


def certification_evidence_lines(policy: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for row in list(policy.get("admissible_rows") or []):
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        issuer = str(row.get("issuer") or "").strip()
        year = row.get("year")
        if not name:
            continue
        parts = [name]
        if issuer:
            parts.append(issuer)
        line = " — ".join(parts)
        if year:
            line = f"{line} ({year})"
        lines.append(line)
    return lines
