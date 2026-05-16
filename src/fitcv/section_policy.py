"""@meta
name: section_policy
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Shared CV section-policy helpers for generator/validator/settings symmetry.
inputs:
  - CV configuration
  - Candidate profile section rows
  - Evidence-selected certifications
outputs:
  - Policy decision objects and formatted section evidence lines
lifecycle:
  - status: active
"""

from __future__ import annotations

from typing import Any

from fitcv.config import CV_SECTION_KEY_TO_NAME

SECTION_POLICY_STATE_HIDDEN_BY_TOGGLE = "hidden_by_toggle"
SECTION_POLICY_STATE_HIDDEN_BY_INELIGIBLE_DATA = "hidden_by_ineligible_data"
SECTION_POLICY_STATE_INCLUDED = "included"

SECTION_POLICY_GROUP_PROFILE_BASELINE = "profile_baseline"
SECTION_POLICY_GROUP_ROLE_TAILORED = "role_tailored_evidence_coupled"

SECTION_POLICY_GROUP_BY_KEY: dict[str, str] = {
    "summary": SECTION_POLICY_GROUP_ROLE_TAILORED,
    "education": SECTION_POLICY_GROUP_PROFILE_BASELINE,
    "experience": SECTION_POLICY_GROUP_ROLE_TAILORED,
    "skills": SECTION_POLICY_GROUP_ROLE_TAILORED,
    "certifications": SECTION_POLICY_GROUP_ROLE_TAILORED,
    "projects": SECTION_POLICY_GROUP_ROLE_TAILORED,
    "publications": SECTION_POLICY_GROUP_ROLE_TAILORED,
    "languages": SECTION_POLICY_GROUP_PROFILE_BASELINE,
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


def _profile_rows_for_section(section_key: str, profile: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows = profile.get(section_key) if isinstance(profile, dict) else []
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def certification_rows_from_profile(profile: dict[str, Any] | None) -> list[dict[str, Any]]:
    return _profile_rows_for_section("certifications", profile)


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


def _is_meaningful_education_row(row: dict[str, Any]) -> bool:
    fields = (
        row.get("degree"),
        row.get("institution"),
        row.get("field"),
        row.get("start"),
        row.get("end"),
    )
    return any(str(value or "").strip() and not _is_placeholder_token(value) for value in fields)


def _is_meaningful_language_row(row: dict[str, Any]) -> bool:
    fields = (
        row.get("name"),
        row.get("level"),
        row.get("read"),
        row.get("write"),
        row.get("speak"),
        row.get("notes"),
    )
    if row.get("native"):
        return True
    return any(str(value or "").strip() and not _is_placeholder_token(value) for value in fields)


def _meaningful_rows_for_section(section_key: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if section_key == "certifications":
        return meaningful_certification_rows(rows)
    if section_key == "education":
        return [row for row in rows if _is_meaningful_education_row(row)]
    if section_key == "languages":
        return [row for row in rows if _is_meaningful_language_row(row)]
    return rows


def section_policy_decisions(
    *,
    section_key: str,
    config: dict[str, Any],
    profile: dict[str, Any] | None,
    evidence_selected_certifications: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    section_name = CV_SECTION_KEY_TO_NAME.get(section_key, section_key.title())
    enabled = _section_enabled(config, section_key)
    group = SECTION_POLICY_GROUP_BY_KEY.get(section_key, SECTION_POLICY_GROUP_ROLE_TAILORED)

    profile_rows = _profile_rows_for_section(section_key, profile)
    meaningful_profile_rows = _meaningful_rows_for_section(section_key, profile_rows)

    evidence_rows: list[dict[str, Any]] = []
    meaningful_evidence_rows: list[dict[str, Any]] = []
    admissible_rows: list[dict[str, Any]] = []
    admissible_via = "none"

    if not enabled:
        state = SECTION_POLICY_STATE_HIDDEN_BY_TOGGLE
        required = False
        reason_code = "toggle_disabled"
    elif group == SECTION_POLICY_GROUP_PROFILE_BASELINE:
        if meaningful_profile_rows:
            state = SECTION_POLICY_STATE_INCLUDED
            required = True
            admissible_rows = meaningful_profile_rows
            admissible_via = "profile"
            reason_code = "eligible_profile_data"
        else:
            state = SECTION_POLICY_STATE_HIDDEN_BY_INELIGIBLE_DATA
            required = False
            reason_code = "no_profile_data"
    elif section_key == "certifications":
        evidence_rows = [row for row in (evidence_selected_certifications or []) if isinstance(row, dict)]
        meaningful_evidence_rows = meaningful_certification_rows(evidence_rows)
        admissible_rows = meaningful_evidence_rows
        admissible_via = "evidence" if meaningful_evidence_rows else "none"
        if admissible_rows:
            state = SECTION_POLICY_STATE_INCLUDED
            required = True
            reason_code = "eligible_selected_evidence"
        else:
            state = SECTION_POLICY_STATE_HIDDEN_BY_INELIGIBLE_DATA
            required = False
            reason_code = "no_eligible_evidence"
    else:
        state = SECTION_POLICY_STATE_INCLUDED
        required = True
        reason_code = "enabled_by_toggle"

    return {
        "section_key": section_key,
        "section_name": section_name,
        "group": group,
        "enabled": enabled,
        "state": state,
        "reason_code": reason_code,
        "profile_rows": profile_rows,
        "meaningful_profile_rows": meaningful_profile_rows,
        "evidence_rows": evidence_rows,
        "meaningful_evidence_rows": meaningful_evidence_rows,
        "admissible_rows": admissible_rows,
        "admissible_via": admissible_via,
        "required": required,
    }


def certification_policy_decisions(
    *,
    config: dict[str, Any],
    profile: dict[str, Any] | None,
    evidence_selected_certifications: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    # Backward-compatible alias retained for existing callers.
    return section_policy_decisions(
        section_key="certifications",
        config=config,
        profile=profile,
        evidence_selected_certifications=evidence_selected_certifications,
    )


def section_effective_state_label(state: str, reason_code: str) -> str:
    if state == SECTION_POLICY_STATE_INCLUDED:
        return "Included"
    if state == SECTION_POLICY_STATE_HIDDEN_BY_TOGGLE:
        return "Hidden (toggle)"
    if reason_code == "no_profile_data":
        return "Hidden (no data)"
    return "Hidden (eligibility)"


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
