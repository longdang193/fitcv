"""@meta
name: cv_generator
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.cv_generator.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import tempfile
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlsplit

from jinja2 import BaseLoader, Environment, TemplateError

from fitcv.candidate_name_policy import resolved_candidate_profile_name
from fitcv.candidate import flatten_skills
from fitcv.placeholder_policy import (
    is_placeholder_token as _shared_is_placeholder_token,
    normalize_placeholder_token as _shared_normalize_placeholder_token,
)
from fitcv.config import (
    CV_SECTION_KEY_TO_NAME,
    CV_STRUCTURED_SECTION_KEYS,
    MYCVS_V1_AUDIT_LINE_RE,
    MYCVS_V1_HEADINGS,
    MYCVS_V1_METADATA_LINE_RE,
    get_cv_generation_structured_prompt_id,
    get_cv_renderer_strategy,
    get_prompt_replacement,
    get_required_structured_section_keys,
)
from fitcv.contracts import (
    ANALYSIS_CHANNEL_DEFINITIONS,
    DOMAIN_ALIGNMENT_CHANNEL,
    FINAL_ARTIFACT_CONTRACT_VERSION,
    REQUIRED_SKILL_SUPPORT_CHANNEL,
    RESPONSIBILITY_ALIGNMENT_CHANNEL,
    ROLE_ALIGNMENT_CHANNEL,
    STRUCTURED_CV_SCHEMA_VERSION,
)
from fitcv.cv_presets import get_section_order
from fitcv.prompts import render_prompt
from fitcv.section_policy import (
    certification_evidence_lines,
    certification_policy_decisions,
    resolve_mycvs_v1_policy,
)
from fitcv.llm_runtime import (
    LlmAdapter,
    LlmAdapterResponse,
    LlmRuntimeResult,
    LlmTaskRequest,
    LlmValidationResult,
    execute_llm_task,
    project_llm_runtime_evidence,
)
from fitcv.runtime_routing import resolve_llm_routing
from fitcv.rule_filter import canonicalize_skill

# ── template variant map ─────────────────────────────────────────────────────
# Maps job_family values (populated by enrichment) to styling hints.
# No new classification is performed here — job_family is read as-is.

_TEMPLATE_VARIANTS: dict[str, str] = {
    "data_engineering": "engineering",
    "analytics":        "analytics",
    "data_science":     "science",
    "ml_engineering":   "engineering",
}

_DEFAULT_VARIANT = "standard"
DEFAULT_CV_LOCALE = "en"
DEFAULT_SUPPORTING_EVIDENCE_PER_ROLE = 1
LEGACY_MARKDOWN_PROMPT_ID = "cv_generation.write.v1"
NATIVE_RENDER_CONTRACT_VERSION = "fitcv_native_render_v1"
_EDUCATION_PLACEHOLDER_TOKENS = {
    "",
    "none",
    "null",
    "n/a",
    "na",
    "not specified",
    "not provided",
    "unknown",
}


_RENDER_CONTRACT_VERSION = "cv_native_render_v2"
MYCVS_V1_RENDERER_CONTRACT_VERSION = "mycvs_v1"
CV_CONTENT_PLAN_VERSION = "cv_content_plan_v1"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")

def _is_mycvs_v1_composition_plan(
    content_plan: Any,
    config: dict[str, Any] | None = None,
) -> bool:
    return (
        isinstance(content_plan, dict)
        and str(content_plan.get("schema_version") or "").strip() == CV_CONTENT_PLAN_VERSION
        and isinstance(content_plan.get("section_policy"), dict)
        and (
            str(content_plan.get("renderer_strategy") or "").strip() == "mycvs_v1"
            or (
                "renderer_strategy" not in content_plan
                and config is not None
                and get_cv_renderer_strategy(config) == "mycvs_v1"
            )
            or "renderer_strategy" not in content_plan and config is None
        )
    )

def _runtime_project_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    return Path(frozen_root) if frozen_root else Path(__file__).resolve().parents[2]


_BUNDLED_MYCVS_RENDERER_DIR = _runtime_project_root() / "scripts" / "renderers" / "mycvs_v1"


def _stable_render_fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def build_render_proof_identity(structured_cv: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    proof = {
        "final_artifact_contract_version": FINAL_ARTIFACT_CONTRACT_VERSION,
        "artifact_content_sha256": _stable_render_fingerprint(structured_cv),
        "template_sha256": _template_sha256(config) or "",
        "render_config_fingerprint": _render_config_fingerprint(config),
        "renderer_contract_version": _RENDER_CONTRACT_VERSION,
        "renderer_strategy": get_cv_renderer_strategy(config),
    }
    if proof["renderer_strategy"] == "mycvs_v1":
        _, handoff = _mycvs_handoff_context(structured_cv)
        proof["handoff_fingerprint"] = handoff
    return proof


def _trim_item_identity(item: Any) -> str:
    if not isinstance(item, dict):
        return str(item or "").strip().casefold()
    for key in ("canonical_record_id", "evidence_id", "claim_id", "id", "name", "title"):
        value = str(item.get(key) or "").strip()
        if value:
            return value.casefold()
    return _stable_render_fingerprint(item)


def select_template_variant(jd: dict[str, Any]) -> str:
    """Return a template variant name for the given enriched job description.

    Reads ``jd["job_family"]`` (populated by the enrichment stage).
    No new classification is performed — the value is used as a lookup key only.
    Unknown or missing job_family → ``"standard"`` (safe default).
    """
    family = str(jd.get("job_family") or "").strip().lower()
    return _TEMPLATE_VARIANTS.get(family, _DEFAULT_VARIANT)


def _get_enabled_section_names(config: dict[str, Any] | None) -> list[str]:
    if config is None:
        return []
    if get_cv_renderer_strategy(config) == "mycvs_v1":
        return [
            CV_SECTION_KEY_TO_NAME[key]
            for key in resolve_mycvs_v1_policy(config)["section_order"]
        ]
    composition = (config.get("cv") or {}).get("composition") or {}
    enabled_sections: list[str] = []
    preset = str((config.get("cv") or {}).get("preset") or "europass").strip().lower()
    ordered_keys = list(get_section_order(preset))
    ordered_keys.extend(str(key) for key in composition if str(key) not in ordered_keys)
    for section_key in ordered_keys:
        section_cfg = composition.get(section_key)
        if isinstance(section_cfg, dict) and section_cfg.get("enabled", True):
            enabled_sections.append(CV_SECTION_KEY_TO_NAME.get(section_key, section_key.title()))
    return enabled_sections




def _filter_template_by_enabled_sections(template: str, enabled_sections: list[str]) -> str:
    if not enabled_sections:
        return template

    preamble_lines: list[str] = []
    section_blocks: dict[str, list[str]] = {}
    current_section: str | None = None
    has_seen_section = False

    for line in template.splitlines():
        if line.startswith("## "):
            has_seen_section = True
            current_section = line[3:].strip()
            section_blocks[current_section] = [line]
            continue
        if not has_seen_section:
            preamble_lines.append(line)
            continue
        if current_section is not None:
            section_blocks[current_section].append(line)

    filtered_blocks: list[str] = []
    for section_name in enabled_sections:
        block = section_blocks.get(section_name)
        if block:
            filtered_blocks.append("\n".join(block).strip())

    if not filtered_blocks:
        return template

    preamble = "\n".join(preamble_lines).strip()
    parts = [part for part in [preamble, *filtered_blocks] if part]
    return "\n\n".join(parts) + "\n"


def _format_certification_lines(profile: dict[str, Any] | None) -> list[str]:
    if not profile:
        return []

    lines: list[str] = []
    for cert in profile.get("certifications") or []:
        if not isinstance(cert, dict):
            continue
        name = str(cert.get("name") or "").strip()
        if not name:
            continue
        issuer = str(cert.get("issuer") or "").strip()
        year = cert.get("year")
        parts = [name]
        if issuer:
            parts.append(issuer)
        line = " \u2014 ".join(parts)
        if year:
            line = f"{line} ({year})"
        lines.append(line)
    return lines


def _format_language_lines(profile: dict[str, Any] | None) -> list[str]:
    if not profile:
        return []

    lines: list[str] = []
    for language in profile.get("languages") or []:
        if not isinstance(language, dict):
            continue
        name = str(language.get("name") or "").strip()
        if not name:
            continue
        if language.get("native"):
            lines.append(f"{name} (native)")
            continue

        proficiency_parts: list[str] = []
        for label, key in (("read", "read"), ("write", "write"), ("speak", "speak")):
            level = str(language.get(key) or "").strip()
            if level:
                proficiency_parts.append(f"{label}: {level}")

        line = name
        if proficiency_parts:
            line = f"{line} ({', '.join(proficiency_parts)})"
        notes = str(language.get("notes") or "").strip()
        if notes:
            line = f"{line} — {notes}"
        lines.append(line)
    return lines

def _format_education_lines(profile: dict[str, Any] | None) -> list[str]:
    if not profile:
        return []

    lines: list[str] = []
    for education in profile.get("education") or []:
        if not isinstance(education, dict):
            continue
        degree = str(education.get("degree") or "").strip()
        institution = str(education.get("institution") or "").strip()
        if not degree and not institution:
            continue

        field = str(education.get("field") or "").strip()
        start = str(education.get("start") or "").strip()
        end = str(education.get("end") or "").strip()

        parts = [part for part in (degree, institution) if part]
        line = " \u2014 ".join(parts)
        if field:
            line = f"{line} ({field})"
        if start or end:
            line = f"{line} [{ '\u2013'.join(part for part in (start, end) if part) }]"
        lines.append(line)
    return lines


def _format_evidence_block(item: dict[str, Any]) -> str:
    evidence_type = str(item.get("evidence_type") or "")
    if evidence_type == "experience_entry":
        role = str(item.get("role") or "").strip()
        company = str(item.get("company") or "").strip()
        start = str(item.get("start") or "").strip()
        end = str(item.get("end") or "").strip()
        dates = " to ".join(part for part in (start, end) if part) or "(dates unavailable)"
        bullet_lines = [
            f"- {bullet}"
            for bullet in item.get("bullets") or []
            if isinstance(bullet, str) and bullet.strip()
        ]
        skills = ", ".join(str(skill).strip() for skill in item.get("skills") or [] if str(skill).strip())
        parts = [
            "Experience Entry",
            f"Role: {role or '(role unavailable)'}",
            f"Company: {company or '(company unavailable)'}",
            f"Dates: {dates}",
        ]
        if skills:
            parts.append(f"Skills: {skills}")
        if bullet_lines:
            parts.append("Relevant bullets:")
            parts.extend(bullet_lines)
        return "\n".join(parts)
    if evidence_type == "project_entry":
        name = str(item.get("name") or "").strip()
        duration = str(item.get("duration") or "").strip()
        business_value = str(item.get("business_value") or "").strip()
        tech_stack = [
            f"- {line}"
            for line in item.get("tech_stack") or []
            if isinstance(line, str) and line.strip()
        ]
        highlights = [
            f"- {line}"
            for line in item.get("highlights") or []
            if isinstance(line, str) and line.strip()
        ]
        parts = [
            "Project Entry",
            f"Name: {name or '(name unavailable)'}",
        ]
        if duration:
            parts.append(f"Duration: {duration}")
        if business_value:
            parts.append(f"Business value: {business_value}")
        if tech_stack:
            parts.append("Relevant stack:")
            parts.extend(tech_stack)
        if highlights:
            parts.append("Relevant highlights:")
            parts.extend(highlights)
        return "\n".join(parts)
    if evidence_type == "candidate_evidence":
        source_section = str(item.get("source_section") or "").strip().lower()
        text = str(item.get("text") or item.get("name") or "").strip()
        if source_section == "experiences":
            role = str(item.get("parent_title") or item.get("role") or "").strip()
            company = str(item.get("organization") or item.get("company") or "").strip()
            skills = ", ".join(str(skill).strip() for skill in item.get("skills") or [] if str(skill).strip())
            parts = [
                "Selected Experience Evidence",
                f"Role: {role or '(role unavailable)'}",
                f"Company: {company or '(company unavailable)'}",
                f"Relevant bullet: {text or '(text unavailable)'}",
            ]
            if skills:
                parts.append(f"Skills: {skills}")
            return "\n".join(parts)
        if source_section == "projects":
            project_name = str(item.get("parent_title") or item.get("name") or "").strip()
            return "\n".join(
                [
                    "Selected Project Evidence",
                    f"Name: {project_name or '(name unavailable)'}",
                    f"Relevant detail: {text or '(text unavailable)'}",
                ]
            )
        if source_section:
            return "\n".join(
                [
                    f"Selected {source_section.title()} Evidence (not work history)",
                    f"Relevant detail: {text or '(text unavailable)'}",
                ]
            )

    name = str(item.get("name", "Unknown"))
    skills = ", ".join(item.get("skills") or [])
    return f"- {name}: {skills}"


def _supporting_evidence_priority(evidence_type: str) -> int:
    priorities = {
        "achievement": 0,
        "project_entry": 1,
        "project": 2,
    }
    return priorities.get(evidence_type, 9)


def _supporting_evidence_score(
    *,
    experience_item: dict[str, Any],
    support_item: dict[str, Any],
    jd_skills: list[str],
) -> int:
    experience_skills = {
        str(skill).strip().lower()
        for skill in experience_item.get("skills") or []
        if str(skill).strip()
    }
    support_skills = {
        str(skill).strip().lower()
        for skill in support_item.get("skills") or []
        if str(skill).strip()
    }
    jd_skill_set = {str(skill).strip().lower() for skill in jd_skills if str(skill).strip()}
    return len(experience_skills & support_skills) + len(jd_skill_set & support_skills)


def _format_supporting_evidence_line(item: dict[str, Any]) -> str:
    evidence_type = str(item.get("evidence_type") or "")
    name = str(item.get("name") or "").strip() or "Unknown"
    label = {
        "achievement": "Achievement",
        "project_entry": "Related project",
        "project": "Related project",
    }.get(evidence_type, "Supporting evidence")
    return f"- {label}: {name}"


def _select_supporting_evidence_for_experience(
    *,
    experience_item: dict[str, Any],
    evidence: list[dict[str, Any]],
    jd_skills: list[str],
    enabled_section_names: list[str],
) -> list[dict[str, Any]]:
    projects_enabled = "Projects" in enabled_section_names
    candidates: list[dict[str, Any]] = []
    for item in evidence:
        evidence_type = str(item.get("evidence_type") or "")
        if evidence_type not in {"achievement", "project_entry", "project"}:
            continue
        if evidence_type in {"project_entry", "project"} and projects_enabled:
            continue
        score = _supporting_evidence_score(
            experience_item=experience_item,
            support_item=item,
            jd_skills=jd_skills,
        )
        if score <= 0:
            continue
        candidates.append(item)

    candidates.sort(
        key=lambda item: (
            -_supporting_evidence_score(
                experience_item=experience_item,
                support_item=item,
                jd_skills=jd_skills,
            ),
            _supporting_evidence_priority(str(item.get("evidence_type") or "")),
            str(item.get("name") or ""),
        )
    )
    return candidates[:DEFAULT_SUPPORTING_EVIDENCE_PER_ROLE]


def _build_selected_evidence_lines(
    evidence: list[dict[str, Any]],
    *,
    jd_skills: list[str],
    enabled_section_names: list[str],
) -> str:
    lines: list[str] = []
    has_experience_entries = any(
        str(item.get("evidence_type") or "") == "experience_entry"
        or (
            str(item.get("evidence_type") or "") == "candidate_evidence"
            and str(item.get("source_section") or "").strip().lower() == "experiences"
        )
        for item in evidence
    )
    for item in evidence:
        evidence_type = str(item.get("evidence_type") or "")
        if evidence_type == "achievement" and has_experience_entries:
            continue
        if evidence_type in {"project_entry", "project"} and has_experience_entries and "Projects" not in enabled_section_names:
            continue

        block = _format_evidence_block(item)
        matched_channels = _coerce_string_list(item.get("matched_channels"))
        selection_reasons = _coerce_string_list(item.get("selection_reasons"))
        metadata_lines: list[str] = []
        if matched_channels:
            metadata_lines.append(
                "Matched channels: " + ", ".join(matched_channels)
            )
        if selection_reasons:
            metadata_lines.append(
                "Selection reasons: " + ", ".join(selection_reasons)
            )
        if evidence_type == "experience_entry":
            supporting_items = _select_supporting_evidence_for_experience(
                experience_item=item,
                evidence=evidence,
                jd_skills=jd_skills,
                enabled_section_names=enabled_section_names,
            )
            if supporting_items:
                support_lines = [_format_supporting_evidence_line(support_item) for support_item in supporting_items]
                metadata_lines.extend(["Supporting evidence:", *support_lines])
        if metadata_lines:
            block = "\n".join([block, *metadata_lines])
        lines.append(block)
    return "\n".join(lines) or "(none)"


def _build_evidence_usage_guidance(evidence: list[dict[str, Any]]) -> str:
    matched_channels = {
        channel
        for item in evidence
        for channel in _coerce_string_list(item.get("matched_channels"))
    }
    selection_reasons = {
        reason
        for item in evidence
        for reason in _coerce_string_list(item.get("selection_reasons"))
    }
    channels_or_reasons = matched_channels | selection_reasons
    if not channels_or_reasons:
        return "(no channel-aware evidence guidance available)"

    guidance_by_channel = {
        REQUIRED_SKILL_SUPPORT_CHANNEL: f"Use evidence tagged `{REQUIRED_SKILL_SUPPORT_CHANNEL}` to justify concrete technical and skills claims.",
        ROLE_ALIGNMENT_CHANNEL: f"Use evidence tagged `{ROLE_ALIGNMENT_CHANNEL}` to shape the summary, headline, and role positioning.",
        DOMAIN_ALIGNMENT_CHANNEL: f"Use evidence tagged `{DOMAIN_ALIGNMENT_CHANNEL}` only for grounded domain familiarity or business-context claims.",
        RESPONSIBILITY_ALIGNMENT_CHANNEL: f"Use evidence tagged `{RESPONSIBILITY_ALIGNMENT_CHANNEL}` to craft experience bullets around similar work and outcomes.",
    }
    guidance_lines = [
        guidance_by_channel[channel_definition.channel_id]
        for channel_definition in ANALYSIS_CHANNEL_DEFINITIONS.values()
        if channel_definition.channel_id in channels_or_reasons
    ]
    guidance_lines.append(
        "Prefer evidence selected by multiple channels when deciding what to emphasize in the final CV."
    )
    return "\n".join(f"- {line}" for line in guidance_lines)


def _profile_contact_value(profile: dict[str, Any] | None, key: str) -> str | None:
    if not profile:
        return None
    direct_value = profile.get(key)
    if isinstance(direct_value, str) and direct_value.strip():
        return direct_value.strip()
    contact = profile.get("contact")
    if isinstance(contact, dict):
        nested_value = contact.get(key)
        if isinstance(nested_value, str) and nested_value.strip():
            return nested_value.strip()
    return None


def project_authorized_profile(
    profile: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    *,
    preserve_canonical: bool = False,
) -> dict[str, Any]:
    """Keep identity and only profile records represented by authorized evidence."""
    if evidence is None or preserve_canonical:
        return deepcopy(profile)
    selected_ids = {
        str(value)
        for item in evidence
        for value in (item.get("evidence_id"), item.get("parent_id"), item.get("id"))
        if str(value or "").strip()
    }
    projected: dict[str, Any] = {}
    for key, value in profile.items():
        if key in {"name", "contact", "email", "phone", "linkedin", "github", "location"}:
            projected[key] = deepcopy(value)
            continue
        if not isinstance(value, list):
            continue
        selected_items = []
        for item in value:
            if not isinstance(item, dict):
                continue
            item_ids = {
                str(candidate)
                for candidate in (item.get("id"), item.get("evidence_id"), item.get("parent_id"))
                if str(candidate or "").strip()
            }
            item_ids.update(
                str(child.get("id") or child.get("evidence_id"))
                for child in list(item.get("evidence") or item.get("bullets") or [])
                if isinstance(child, dict) and str(child.get("id") or child.get("evidence_id") or "").strip()
            )
            if item_ids & selected_ids:
                selected_items.append(deepcopy(item))
        projected[key] = selected_items
    return projected


def _project_authorized_gap(
    gap: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    projected = deepcopy(gap)
    allowed_skills = {
        canonicalize_skill(str(skill))
        for item in evidence
        for skill in list(item.get("skills") or [])
        if str(skill).strip()
    }
    projected["matched"] = [
        skill
        for skill in list(gap.get("matched") or [])
        if canonicalize_skill(str(skill)) in allowed_skills
    ]
    coverage = []
    for item in list(gap.get("requirement_coverage") or []):
        if not isinstance(item, dict):
            continue
        selected_support = str(item.get("selected_support") or "").strip().lower()
        requirement = canonicalize_skill(str(item.get("requirement") or ""))
        if selected_support in {"selected_supported", "supported"} or requirement in allowed_skills:
            coverage.append(deepcopy(item))
    if "requirement_coverage" in gap:
        projected["requirement_coverage"] = coverage
    return projected


def _coerce_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                result.append(stripped)
    return result


def _build_generation_prompt_context(
    *,
    jd: dict[str, Any],
    evidence: list[dict[str, Any]],
    gap: dict[str, Any],
    template: str,
    profile: dict[str, Any] | None,
    config: dict[str, Any] | None,
    evidence_selection_summary: dict[str, Any] | None,
    repair_missing_sections: list[str] | None,
    content_plan: dict[str, Any] | None,
    target_sections: list[str] | None,
) -> dict[str, str]:
    title = str(jd.get("title") or "")
    required_skills = list(jd.get("required_skills") or [])
    candidate_name = resolved_candidate_profile_name(profile)

    composition_mode = _is_mycvs_v1_composition_plan(content_plan, config)
    enabled_section_names = _get_enabled_section_names(config)

    allowed_skill_set = _collect_allowed_skill_set(evidence, config=config)
    allowed_skills = sorted(skill for skill in allowed_skill_set if skill)

    allowed_certifications: list[str] = []
    if not composition_mode and "Certifications" in enabled_section_names and not allowed_certifications:
        enabled_section_names = [name for name in enabled_section_names if name != "Certifications"]
    prompt_required_sections = ["Summary"] if composition_mode else enabled_section_names

    evidence_lines = _build_selected_evidence_lines(
        evidence,
        jd_skills=required_skills,
        enabled_section_names=enabled_section_names,
    )
    evidence_usage_guidance = _build_evidence_usage_guidance(evidence)

    matched_skills = list(gap.get("matched") or [])
    missing_skills = list(gap.get("missing") or [])

    constraint_lines: list[str] = []
    if missing_skills:
        constraint_lines.append(
            "Do NOT claim the candidate has the following skills "
            f"(they are missing from their profile): {', '.join(missing_skills)}"
        )
    do_not_claim = [str(item) for item in list(gap.get("do_not_claim") or []) if str(item)]
    if do_not_claim:
        constraint_lines.append(
            "Do NOT claim the following unsupported items: "
            + ", ".join(do_not_claim)
        )
    if matched_skills:
        constraint_lines.append(
            f"The candidate does have: {', '.join(matched_skills)}"
        )
    if profile:
        if candidate_name:
            constraint_lines.append(
                f"Use this exact candidate name in the header: {candidate_name}"
            )
            constraint_lines.append(
                "Do not output placeholder names such as Candidate Name, [Candidate Name], Your Name, or [Your Name]."
            )
        selected_employers = sorted(
            {
                str(item.get("company") or item.get("organization") or "").strip()
                for item in evidence
                if (
                    str(item.get("evidence_type") or "").strip().lower() == "experience_entry"
                    or (
                        str(item.get("evidence_type") or "").strip().lower() == "candidate_evidence"
                        and str(item.get("source_section") or "").strip().lower() == "experiences"
                    )
                )
                and str(item.get("company") or item.get("organization") or "").strip()
            }
        )
        selected_projects = sorted(
            {
                str(item.get("parent_title") or item.get("name") or "").strip()
                for item in evidence
                if (
                    str(item.get("evidence_type") or "").strip().lower() in {"project", "project_entry"}
                    or (
                        str(item.get("evidence_type") or "").strip().lower() == "candidate_evidence"
                        and str(item.get("source_section") or "").strip().lower() == "projects"
                    )
                )
                and str(item.get("parent_title") or item.get("name") or "").strip()
            }
        )
        selected_experience_evidence = any(
            str(item.get("evidence_type") or "").strip().lower() == "experience_entry"
            or (
                str(item.get("evidence_type") or "").strip().lower() == "candidate_evidence"
                and str(item.get("source_section") or "").strip().lower() == "experiences"
            )
            for item in evidence
        )
        has_non_experience_evidence = any(
            str(item.get("evidence_type") or "").strip().lower() == "candidate_evidence"
            and str(item.get("source_section") or "").strip().lower() != "experiences"
            for item in evidence
        )
        if not composition_mode and selected_employers:
            constraint_lines.append(
                "Only use employers named in selected evidence: "
                + ", ".join(selected_employers)
            )
        elif not composition_mode and evidence:
            constraint_lines.append(
                "Do not include employer names unless they appear in selected evidence."
            )
            constraint_lines.append(
                "No selected experience evidence exists: set the Experience section to [] and do not convert project, education, or achievement evidence into work history."
            )
        if not composition_mode and selected_experience_evidence:
            constraint_lines.append(
                "Use only selected Experience evidence for the Experience section; never convert education, achievement, volunteering, or project evidence into employment."
            )
        elif not composition_mode and has_non_experience_evidence:
            constraint_lines.append(
                "Non-experience evidence belongs only in its matching section; never convert education, achievement, volunteering, or project evidence into employment."
            )
        if not composition_mode and selected_projects:
            constraint_lines.append(
                "Only use project names named in selected evidence: "
                + ", ".join(selected_projects)
            )
            constraint_lines.append(
                "Keep project evidence in the Projects section; never use a project name as an Experience.company or employer."
            )
        elif not composition_mode and evidence:
            constraint_lines.append(
                "Do not include project names unless they appear in selected evidence."
            )
        if not composition_mode and allowed_skills:
            constraint_lines.append(
                "Allowed Skills (selected-evidence only): " + ", ".join(allowed_skills)
            )
            constraint_lines.append(
                "In the Skills section, list only skills from Allowed Skills. Do not add profile-only skills."
            )
    if prompt_required_sections:
        section_requirement = (
            "The generated CV MUST include these mandatory sections: "
            if composition_mode
            else "The generated CV MUST include these sections in this order: "
        )
        constraint_lines.append(section_requirement + ", ".join(prompt_required_sections))
        constraint_lines.append(
            "Use markdown headings exactly: '# {Candidate Name}', optional one-line subtitle, then each required section as '## Section'."
        )
        constraint_lines.append(
            "Use '- ' as the only bullet marker and keep exactly one blank line between top-level sections."
        )
    if repair_missing_sections:
        constraint_lines.append(
            "Regenerate the CV and fix the previous structural failure by including these missing sections with grounded content: "
            + ", ".join(repair_missing_sections)
        )
        constraint_lines.append(
            "Do not leave required sections empty. Each required section must contain at least one grounded line or bullet."
        )
    approved_claims = [
        item for item in list((content_plan or {}).get("approved_claims") or []) if isinstance(item, dict)
    ]
    has_approved_job_claims = bool(approved_claims)
    allow_baseline_profile = (
        isinstance(content_plan, dict)
        and "approved_claims" in content_plan
        and not approved_claims
    )
    if content_plan:
        if composition_mode:
            constraint_lines.extend(
                [
                    "Use the canonical candidate profile as the factual baseline for Header, Education, Experience, Projects, Certifications, and Skills.",
                    "Use selected job evidence only to tailor relevance and support job-specific claims; selected evidence must not erase canonical profile records.",
                    "Treat unsupported or unknown requirements as gaps; never turn them into candidate claims.",
                    "Do not expose evidence IDs, requirement IDs, claim IDs, fingerprints, or provenance in recruiter-facing Markdown.",
                    "Summary is mandatory and must contain 2-4 grounded tailored sentences.",
                    "Preserve canonical Experience records with one overview and 3-5 achievement bullets where grounded; preserve canonical Projects and their validated links.",
                    "Certifications come from the canonical profile independently of selected evidence and are omitted only when no meaningful canonical certifications exist.",
                    "Skills start from canonical grounded skills, normalized and deduplicated, then prioritized against the JD; do not invent unsupported job-only skills.",
                ]
            )
        elif has_approved_job_claims:
            constraint_lines.append(
                "Use only approved claims and evidence ids from this cv_content_plan_v1; omit every claim not listed: "
                + json.dumps(content_plan, sort_keys=True, ensure_ascii=False)
            )
        elif allow_baseline_profile:
            constraint_lines.append(
                "No verified job-specific claims were approved. Use factual baseline records from the authorized candidate profile "
                "for the enabled sections; do not leave sections empty solely because approved_claims is empty."
            )
        space_budget = dict(content_plan.get("space_budget") or {})
        max_summary_lines = space_budget.get("max_summary_lines")
        section_limits = dict(space_budget.get("section_claim_limits") or {})
        if max_summary_lines is not None:
            constraint_lines.append(f"Target exactly one rendered page; keep Summary at most {int(max_summary_lines)} lines.")
        if section_limits:
            constraint_lines.append(
                "Keep each section within these claim budgets: "
                + ", ".join(f"{section}={limit}" for section, limit in sorted(section_limits.items()))
                + "."
            )
        constraint_lines.append("Do not add unsupported filler or duplicate claims.")
        if composition_mode:
            constraint_lines.append(
                "Omit optional sections only when their canonical source is genuinely empty; never omit canonical employment, projects, certifications, or grounded Skills to satisfy an evidence allowlist."
            )
        else:
            constraint_lines.append(
                "Omit optional sections deterministically when space is constrained: publications, certifications, languages, then projects."
            )
    if target_sections:
        normalized_targets = [str(item).strip().lower() for item in target_sections if str(item).strip()]
        constraint_lines.append(
            "Return and modify only these section keys: " + ", ".join(normalized_targets)
        )
        constraint_lines.append("Do not return unrelated sections or alter their content.")

    if config is not None:
        composition = (config.get("cv") or {}).get("composition") or {}
        for section_key, section_cfg in composition.items():
            if isinstance(section_cfg, dict) and not section_cfg.get("enabled", True):
                display_name = CV_SECTION_KEY_TO_NAME.get(section_key, section_key.title())
                constraint_lines.append(
                    f"Do NOT include a '{display_name}' section."
                )
    requirement_coverage = [
        dict(item)
        for item in list(gap.get("requirement_coverage") or [])
        if isinstance(item, dict)
    ]
    if requirement_coverage:
        supported = [
            str(item.get("requirement") or "").strip()
            for item in requirement_coverage
            if (
                str(item.get("selected_support") or "").strip().lower() == "verified"
                or (
                    not str(item.get("selected_support") or "").strip()
                    and str(item.get("support_strength") or "").strip().lower() == "supported"
                )
            )
            and str(item.get("requirement") or "").strip()
        ]
        unsupported = [
            str(item.get("requirement") or "").strip()
            for item in requirement_coverage
            if (
                str(item.get("selected_support") or "").strip().lower() == "unsupported"
                or (
                    not str(item.get("selected_support") or "").strip()
                    and str(item.get("support_strength") or "").strip().lower() == "unsupported"
                )
            )
            and str(item.get("requirement") or "").strip()
        ]
        non_authoritative = [
            str(item.get("requirement") or "").strip()
            for item in requirement_coverage
            if str(item.get("selected_support") or "").strip().lower()
            in {"relevant_unverified", "not_selected"}
            and str(item.get("requirement") or "").strip()
        ]
        if supported:
            constraint_lines.append(
                "Prioritize these strongly supported requirements: " + ", ".join(supported)
            )
        if unsupported:
            constraint_lines.append(
                "Treat these requirements as unsupported unless explicit evidence is present: "
                + ", ".join(unsupported)
            )
        if non_authoritative:
            constraint_lines.append(
                "Treat these requirements as non-authoritative for generation: "
                + ", ".join(non_authoritative)
            )
    section_confidence_hints = dict(gap.get("section_confidence_hints") or {})
    if section_confidence_hints:
        hints_text = ", ".join(
            f"{section}={str(level)}"
            for section, level in section_confidence_hints.items()
            if str(section).strip() and str(level).strip()
        )
        if hints_text:
            constraint_lines.append("Section confidence hints: " + hints_text)
    if any(str(item.get("evidence_type") or "") == "experience_entry" for item in evidence):
        constraint_lines.append(
            "For the Experience section, emphasize the bullets most relevant to the target JD."
        )
        constraint_lines.append(
            "For the Experience section, summarize or combine grounded facts where helpful."
        )
    if evidence:
        if composition_mode:
            constraint_lines.append(
                "Selected evidence controls job-specific relevance, emphasis, and claim support; canonical profile facts remain eligible even when not selected."
            )
            constraint_lines.append(
                "Do not invent job-specific claims or present evidence IDs, provenance, or internal metadata in the recruiter-facing CV."
            )
        else:
            constraint_lines.append(
                "Stay within the selected evidence bundle for this job."
            )
            constraint_lines.append(
                "If a responsibility, domain, or role-positioning claim is not supported by the selected evidence, omit it."
            )
        if not composition_mode:
            if has_approved_job_claims:
                constraint_lines.append(
                    "Every summary, experience bullet, and project bullet must be supported by selected evidence text; do not use profile-only technologies or claims."
                )
            elif allow_baseline_profile:
                constraint_lines.append(
                    "Use baseline profile records for factual sections, and use the selected evidence bundle only to tailor job-specific positioning; do not invent facts."
                )
            else:
                constraint_lines.append(
                    "Every summary, experience bullet, and project bullet must be supported by selected evidence text; do not use profile-only technologies or claims."
                )

    constraints = "\n".join(constraint_lines) or "(no specific constraints)"
    filtered_template = _filter_template_by_enabled_sections(template, enabled_section_names)
    section_evidence_lines: list[str] = []
    if "Certifications" in enabled_section_names:
        cert_policy = certification_policy_decisions(
            config=config,
            profile=profile,
            evidence_selected_certifications=[],
        )
        certification_lines = certification_evidence_lines(cert_policy)
        if certification_lines:
            section_evidence_lines.append(
                "Use these candidate certifications when filling the Certifications section:\n"
                + "\n".join(f"- {line}" for line in certification_lines)
            )
    if "Languages" in enabled_section_names:
        language_lines = _format_language_lines(profile)
        if language_lines:
            section_evidence_lines.append(
                "Use these candidate languages when filling the Languages section:\n"
                + "\n".join(f"- {line}" for line in language_lines)
            )
    if "Education" in enabled_section_names:
        education_lines = _format_education_lines(profile)
        if education_lines:
            section_evidence_lines.append(
                "Use these candidate education entries when filling the Education section:\n"
                + "\n".join(f"- {line}" for line in education_lines)
            )
    section_evidence = "\n\n".join(section_evidence_lines) or "(no additional section-specific evidence)"
    analysis_summary_lines: list[str] = []
    if evidence_selection_summary:
        selected_count = evidence_selection_summary.get("selected_evidence_count")
        if selected_count is not None:
            analysis_summary_lines.append(
                f"Selected evidence count: {selected_count}"
            )
        selected_ids = _coerce_string_list(
            evidence_selection_summary.get("selected_evidence_ids")
        )
        if selected_ids:
            analysis_summary_lines.append(
                "Selected evidence ids: " + ", ".join(selected_ids)
            )
        channel_counts = evidence_selection_summary.get("channel_counts")
        if isinstance(channel_counts, dict) and channel_counts:
            ordered_counts = ", ".join(
                f"{key}={channel_counts[key]}"
                for key in sorted(channel_counts)
            )
            analysis_summary_lines.append(
                "Evidence channel counts: " + ordered_counts
            )
    analysis_summary = "\n".join(analysis_summary_lines) or "(no analysis summary available)"
    return {
        "title": title,
        "required_skills": ", ".join(required_skills) or "(none specified)",
        "selected_evidence": evidence_lines,
        "evidence_usage_guidance": evidence_usage_guidance,
        "analysis_summary": analysis_summary,
        "constraints": constraints,
        "allowed_skills": ", ".join(allowed_skills) or "(none)",
        "allowed_certifications": ", ".join(allowed_certifications) or "(none)",
        "section_evidence": section_evidence,
        "output_template": filtered_template,
    }


def _build_default_sections(
    *,
    profile: dict[str, Any] | None,
    jd: dict[str, Any],
) -> dict[str, Any]:
    return {
        "header": {
            "name": str((profile or {}).get("name") or "").strip(),
            "title": str(jd.get("title") or "").strip(),
            "location": _profile_contact_value(profile, "location"),
            "contact": {
                "email": _profile_contact_value(profile, "email"),
                "phone": _profile_contact_value(profile, "phone"),
                "linkedin": _profile_contact_value(profile, "linkedin"),
                "github": _profile_contact_value(profile, "github"),
            },
        },
        "summary": {"text": ""},
        "experience": [],
        "projects": [],
        "education": [],
        "skills": {"groups": []},
        "certifications": [],
        "publications": [],
        "languages": [],
    }


def build_empty_structured_cv(
    *,
    jd: dict[str, Any],
    profile: dict[str, Any] | None,
    config: dict[str, Any],
    fit_classification: str,
) -> dict[str, Any]:
    """Return the canonical empty structured CV document for one generation run."""
    cv_cfg = config.get("cv") or {}
    return {
        "schema_version": STRUCTURED_CV_SCHEMA_VERSION,
        "preset": str(cv_cfg.get("preset") or ""),
        "locale": str(cv_cfg.get("locale") or DEFAULT_CV_LOCALE),
        "job_url": str(jd.get("job_url") or ""),
        "fit_classification": str(fit_classification or "unclassified"),
        "target_role": str(jd.get("title") or ""),
        "sections": _build_default_sections(profile=profile, jd=jd),
    }


def build_live_structured_cv_response_schema(config: dict[str, Any] | None = None) -> dict[str, Any]:
    nullable_string_schema = {
        "anyOf": [
            {"type": "string"},
            {"type": "null"},
        ]
    }
    bullet_schema = {
        "type": "string",
    }
    required_sections = [
        "header",
        "summary",
        "experience",
        "projects",
        "education",
        "skills",
        "certifications",
        "publications",
        "languages",
    ]
    if config is not None:
        if get_cv_renderer_strategy(config) == "mycvs_v1":
            required_sections = ["header", "summary"]
        else:
            required_sections = ["header", *get_required_structured_section_keys(config)]
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["sections"],
        "properties": {
            "sections": {
                "type": "object",
                "additionalProperties": False,
                "required": required_sections,
                "properties": {
                    "header": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "title", "location", "contact"],
                        "properties": {
                            "name": {"type": "string"},
                            "title": {"type": "string"},
                            "location": nullable_string_schema,
                            "contact": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["email", "phone", "linkedin", "github"],
                                "properties": {
                                    "email": nullable_string_schema,
                                    "phone": nullable_string_schema,
                                    "linkedin": nullable_string_schema,
                                    "github": nullable_string_schema,
                                },
                            },
                        },
                    },
                    "summary": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["text"],
                        "properties": {
                            "text": {"type": "string"},
                        },
                    },
                    "experience": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["role", "company", "start", "end", "location", "bullets"],
                            "properties": {
                                "role": {"type": "string"},
                                "company": {"type": "string"},
                                "start": nullable_string_schema,
                                "end": nullable_string_schema,
                                "location": nullable_string_schema,
                                "bullets": {"type": "array", "items": bullet_schema},
                            },
                        },
                    },
                    "projects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["name", "context", "url", "bullets"],
                            "properties": {
                                "name": {"type": "string"},
                                "context": nullable_string_schema,
                                "url": nullable_string_schema,
                                "bullets": {"type": "array", "items": bullet_schema},
                            },
                        },
                    },
                    "education": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["degree", "institution", "field", "start", "end"],
                            "properties": {
                                "degree": {"type": "string"},
                                "institution": {"type": "string"},
                                "field": nullable_string_schema,
                                "start": nullable_string_schema,
                                "end": nullable_string_schema,
                            },
                        },
                    },
                    "skills": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["groups"],
                        "properties": {
                            "groups": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": ["label", "items"],
                                    "properties": {
                                        "label": {"type": "string"},
                                        "items": {"type": "array", "items": {"type": "string"}},
                                    },
                                },
                            },
                        },
                    },
                    "certifications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["name", "issuer", "year", "url"],
                            "properties": {
                                "name": {"type": "string"},
                                "issuer": nullable_string_schema,
                                "year": nullable_string_schema,
                                "url": nullable_string_schema,
                            },
                        },
                    },
                    "publications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["title", "publisher", "year"],
                            "properties": {
                                "title": {"type": "string"},
                                "publisher": nullable_string_schema,
                                "year": nullable_string_schema,
                            },
                        },
                    },
                    "languages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["name", "level"],
                            "properties": {
                                "name": {"type": "string"},
                                "level": nullable_string_schema,
                            },
                        },
                    },
                },
            },
        },
    }
    return schema

def validate_structured_cv(
    structured_cv: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> None:
    """Validate the canonical structured CV document shape."""
    required_keys = (
        "schema_version",
        "preset",
        "locale",
        "job_url",
        "fit_classification",
        "target_role",
        "sections",
    )
    missing_keys = [key for key in required_keys if key not in structured_cv]
    if missing_keys:
        raise ValueError(f"Structured CV missing required keys: {', '.join(missing_keys)}")

    sections = structured_cv.get("sections")
    if not isinstance(sections, dict):
        raise ValueError("Structured CV sections must be an object")

    required_sections = set(CV_STRUCTURED_SECTION_KEYS)
    if config is not None:
        if get_cv_renderer_strategy(config) == "mycvs_v1":
            required_sections = {"header", "summary"}
        else:
            required_sections = {"header", *get_required_structured_section_keys(config)}
    missing_sections = [key for key in required_sections if key not in sections]
    if missing_sections:
        raise ValueError(f"Structured CV missing required sections: {', '.join(missing_sections)}")

    if not isinstance(sections["header"], dict):
        raise ValueError("Structured CV header section must be an object")
    if "summary" in sections and not isinstance(sections["summary"], dict):
        raise ValueError("Structured CV summary section must be an object")
    if "skills" in sections and not isinstance(sections["skills"], dict):
        raise ValueError("Structured CV skills section must be an object")

    for list_section in ("experience", "projects", "education", "certifications", "publications", "languages"):
        if list_section in sections and not isinstance(sections[list_section], list):
            raise ValueError(f"Structured CV {list_section} section must be a list")

    if "skills" in sections:
        groups = sections["skills"].get("groups")
        if not isinstance(groups, list):
            raise ValueError("Structured CV skills.groups must be a list")
        for group in groups:
            if not isinstance(group, dict):
                raise ValueError("Structured CV skills.groups entries must be objects")
            if not isinstance(group.get("label"), str) or not group.get("label", "").strip():
                raise ValueError("Structured CV skills.groups entries require a non-empty label")
            if not isinstance(group.get("items"), list):
                raise ValueError("Structured CV skills.groups entries require list items")
            if not all(isinstance(item, str) for item in group["items"]):
                raise ValueError("Structured CV skills.groups items must be strings")


def _extract_json_payload(response_text: str) -> dict[str, Any]:
    stripped = response_text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model response did not contain a JSON object") from None
        parsed = json.loads(stripped[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Structured CV response must be a JSON object")
    return parsed


def _normalize_contact(raw_header: dict[str, Any], default_header: dict[str, Any]) -> dict[str, Any]:
    raw_contact = raw_header.get("contact")
    default_contact = default_header["contact"]
    if not isinstance(raw_contact, dict):
        raw_contact = {}
    return {
        "email": str(raw_contact.get("email") or default_contact.get("email") or "").strip() or None,
        "phone": str(raw_contact.get("phone") or default_contact.get("phone") or "").strip() or None,
        "linkedin": str(raw_contact.get("linkedin") or default_contact.get("linkedin") or "").strip() or None,
        "github": str(raw_contact.get("github") or default_contact.get("github") or "").strip() or None,
    }


def _normalize_bullets(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return _coerce_string_list([
        value.get("text") if isinstance(value, dict) else value
        for value in values
    ])


def _coerce_object_list(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    result: list[dict[str, Any]] = []
    for value in values:
        if isinstance(value, dict):
            result.append(value)
    return result


def _normalize_placeholder_token(value: Any) -> str:
    return _shared_normalize_placeholder_token(value)


def _is_placeholder_token(value: Any) -> bool:
    return _shared_is_placeholder_token(value)


def _is_synthetic_education_entry(entry: dict[str, Any]) -> bool:
    degree = entry.get("degree")
    institution = entry.get("institution")
    field = entry.get("field")
    start = entry.get("start")
    end = entry.get("end")
    all_placeholder = all(
        _is_placeholder_token(value)
        for value in (degree, institution, field, start, end)
    )
    if all_placeholder:
        return True
    if _is_placeholder_token(degree) and _is_placeholder_token(institution):
        if _is_placeholder_token(start) and _is_placeholder_token(end):
            return True
    return False


def _section_enabled(config: dict[str, Any], section_key: str) -> bool:
    composition = ((config.get("cv") or {}).get("composition") or {})
    section_cfg = composition.get(section_key)
    if not isinstance(section_cfg, dict):
        return True
    return bool(section_cfg.get("enabled", True))

def _is_synthetic_experience_entry(entry: dict[str, Any]) -> bool:
    bullets = [bullet for bullet in (entry.get("bullets") or []) if isinstance(bullet, str)]
    if any(not _is_placeholder_token(bullet) for bullet in bullets):
        return False
    return all(
        _is_placeholder_token(value)
        for value in (
            entry.get("role"),
            entry.get("company"),
            entry.get("start"),
            entry.get("end"),
            entry.get("location"),
        )
    )

def _is_synthetic_projects_entry(entry: dict[str, Any]) -> bool:
    bullets = [bullet for bullet in (entry.get("bullets") or []) if isinstance(bullet, str)]
    if any(not _is_placeholder_token(bullet) for bullet in bullets):
        return False
    return _is_placeholder_token(entry.get("name")) and _is_placeholder_token(entry.get("context"))

def _is_synthetic_certifications_entry(entry: dict[str, Any]) -> bool:
    return all(
        _is_placeholder_token(value)
        for value in (entry.get("name"), entry.get("issuer"), entry.get("year"))
    )

def _is_synthetic_publications_entry(entry: dict[str, Any]) -> bool:
    return all(
        _is_placeholder_token(value)
        for value in (entry.get("title"), entry.get("publisher"), entry.get("year"))
    )

def _is_synthetic_languages_entry(entry: dict[str, Any]) -> bool:
    return all(
        _is_placeholder_token(value)
        for value in (entry.get("name"), entry.get("level"))
    )

def _sanitize_section_entries(
    section_key: str,
    entries: list[dict[str, Any]],
    *,
    config: dict[str, Any],
    ignore_enabled: bool = False,
) -> list[dict[str, Any]]:
    if not ignore_enabled and not _section_enabled(config, section_key):
        return []
    checks = {
        "education": _is_synthetic_education_entry,
        "experience": _is_synthetic_experience_entry,
        "projects": _is_synthetic_projects_entry,
        "certifications": _is_synthetic_certifications_entry,
        "publications": _is_synthetic_publications_entry,
        "languages": _is_synthetic_languages_entry,
    }
    checker = checks.get(section_key)
    if checker is None:
        return entries
    return [entry for entry in entries if not checker(entry)]


def _sanitize_education_entries(
    education_entries: list[dict[str, Any]],
    *,
    config: dict[str, Any],
    ignore_enabled: bool = False,
) -> list[dict[str, Any]]:
    return _sanitize_section_entries(
        "education", education_entries, config=config, ignore_enabled=ignore_enabled
    )

def _normalize_header_section(
    raw_sections: dict[str, Any],
    default_sections: dict[str, Any],
    *,
    canonical_only: bool = False,
) -> dict[str, Any]:
    raw_header = raw_sections.get("header")
    if canonical_only or not isinstance(raw_header, dict):
        raw_header = {}
    return {
        "name": str(raw_header.get("name") or default_sections["header"]["name"]).strip(),
        "title": str(raw_header.get("title") or default_sections["header"]["title"]).strip(),
        "location": str(raw_header.get("location") or default_sections["header"]["location"] or "").strip() or None,
        "contact": _normalize_contact(raw_header, default_sections["header"]),
    }

def _normalize_summary_section(raw_sections: dict[str, Any]) -> dict[str, str]:
    raw_summary = raw_sections.get("summary")
    if isinstance(raw_summary, dict):
        summary_text = str(raw_summary.get("text") or "").strip()
    elif isinstance(raw_summary, str):
        summary_text = raw_summary.strip()
    else:
        summary_text = ""
    return {"text": summary_text}

def _normalize_experience_section(raw_sections: dict[str, Any], *, config: dict[str, Any]) -> list[dict[str, Any]]:
    experience_entries: list[dict[str, Any]] = []
    for item in _coerce_object_list(raw_sections.get("experience")):
        entry = {
            "role": str(item.get("role") or "").strip(),
            "company": str(item.get("company") or "").strip(),
            "start": str(item.get("start") or "").strip() or None,
            "end": str(item.get("end") or "").strip() or None,
            "location": str(item.get("location") or "").strip() or None,
            "bullets": _normalize_bullets(item.get("bullets")),
        }
        if str(item.get("overview") or "").strip():
            entry["overview"] = str(item.get("overview")).strip()
        experience_entries.append(entry)
    return _sanitize_section_entries("experience", experience_entries, config=config)

def _normalize_projects_section(raw_sections: dict[str, Any], *, config: dict[str, Any]) -> list[dict[str, Any]]:
    project_entries: list[dict[str, Any]] = []
    for item in _coerce_object_list(raw_sections.get("projects")):
        entry = {
            "name": str(item.get("name") or "").strip(),
            "context": str(item.get("context") or "").strip() or None,
            "url": str(item.get("url") or item.get("link") or "").strip() or None,
            "bullets": _normalize_bullets(item.get("bullets")),
        }
        for date_key in ("start", "end"):
            if str(item.get(date_key) or "").strip():
                entry[date_key] = str(item.get(date_key)).strip()
        if str(item.get("overview") or "").strip():
            entry["overview"] = str(item.get("overview")).strip()
        project_entries.append(entry)
    return _sanitize_section_entries("projects", project_entries, config=config)

def _normalize_education_section(raw_sections: dict[str, Any], *, config: dict[str, Any]) -> list[dict[str, Any]]:
    education_entries: list[dict[str, Any]] = []
    for item in _coerce_object_list(raw_sections.get("education")):
        education_entries.append(
            {
                "degree": str(item.get("degree") or "").strip(),
                "institution": str(item.get("institution") or "").strip(),
                "field": str(item.get("field") or "").strip() or None,
                "start": str(item.get("start") or "").strip() or None,
                "end": str(item.get("end") or "").strip() or None,
            }
        )
    return _sanitize_education_entries(education_entries, config=config)

def _normalize_skills_section(
    raw_sections: dict[str, Any],
    *,
    allowed_skill_set: set[str] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    raw_skills = raw_sections.get("skills")
    raw_groups = raw_skills.get("groups") if isinstance(raw_skills, dict) else []
    normalized_groups: list[dict[str, Any]] = []
    if isinstance(raw_groups, list):
        for group in raw_groups:
            if not isinstance(group, dict):
                continue
            items = _coerce_string_list(group.get("items"))
            if allowed_skill_set is not None:
                items = [
                    item
                    for item in items
                    if canonicalize_skill(item, config or {}) in allowed_skill_set
                ]
            if not items:
                continue
            normalized_groups.append(
                {
                    "label": str(group.get("label") or "").strip(),
                    "items": items,
                }
            )
    return {"groups": normalized_groups}


def _canonical_profile_sections(profile: dict[str, Any] | None, *, config: dict[str, Any]) -> dict[str, Any]:
    """Project canonical profile records into the structured CV shape."""
    profile = profile if isinstance(profile, dict) else {}

    def rows(key: str) -> list[dict[str, Any]]:
        value = profile.get(key)
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    experiences = []
    for item in rows("experiences"):
        experiences.append({
            "canonical_record_id": item.get("id") or item.get("record_id") or item.get("evidence_id"),
            "role": str(item.get("role") or item.get("title") or "").strip(),
            "company": str(item.get("company") or item.get("employer") or "").strip(),
            "start": str(item.get("start") or item.get("start_date") or "").strip() or None,
            "end": str(item.get("end") or item.get("end_date") or "").strip() or None,
            "location": str(item.get("location") or "").strip() or None,
            "overview": str(item.get("overview") or item.get("summary") or item.get("description") or "").strip() or None,
            "bullets": _normalize_bullets(item.get("bullets") or item.get("achievements")),
        })
    projects = []
    for item in rows("projects"):
        projects.append({
            "canonical_record_id": item.get("id") or item.get("record_id") or item.get("evidence_id"),
            "name": str(item.get("name") or item.get("title") or "").strip(),
            "context": str(item.get("context") or item.get("technologies") or "").strip() or None,
            "overview": str(item.get("overview") or item.get("summary") or item.get("description") or "").strip() or None,
            "start": str(item.get("start") or item.get("start_date") or "").strip() or None,
            "end": str(item.get("end") or item.get("end_date") or "").strip() or None,
            "url": str(item.get("url") or item.get("link") or "").strip() or None,
            "bullets": _normalize_bullets(item.get("bullets") or item.get("achievements") or item.get("highlights")),
        })
    education = []
    for item in rows("education"):
        education.append({
            "canonical_record_id": item.get("id") or item.get("record_id") or item.get("evidence_id"),
            "degree": str(item.get("degree") or item.get("qualification") or "").strip(),
            "institution": str(item.get("institution") or item.get("school") or "").strip(),
            "field": str(item.get("field") or item.get("major") or "").strip() or None,
            "start": str(item.get("start") or item.get("start_date") or "").strip() or None,
            "end": str(item.get("end") or item.get("end_date") or "").strip() or None,
            "details": str(item.get("details") or item.get("description") or "").strip() or None,
        })
    certifications = []
    for item in rows("certifications"):
        certifications.append({
            "canonical_record_id": item.get("id") or item.get("record_id") or item.get("evidence_id"),
            "name": str(item.get("name") or item.get("title") or "").strip(),
            "issuer": str(item.get("issuer") or item.get("organization") or "").strip() or None,
            "year": str(item.get("year") or item.get("issue_date") or item.get("date") or "").strip() or None,
            "url": str(item.get("url") or item.get("link") or "").strip() or None,
            "details": str(item.get("details") or item.get("description") or "").strip() or None,
        })
    skill_names = flatten_skills(profile)
    skill_items: list[str] = []
    seen: set[str] = set()
    for skill in skill_names:
        value = str(skill).strip()
        canonical = canonicalize_skill(value, config)
        if value and canonical not in seen:
            seen.add(canonical)
            skill_items.append(value)
    return {
        "experience": _sanitize_section_entries("experience", experiences, config=config, ignore_enabled=True),
        "projects": _sanitize_section_entries("projects", projects, config=config, ignore_enabled=True),
        "education": _sanitize_education_entries(education, config=config, ignore_enabled=True),
        "certifications": _sanitize_section_entries("certifications", certifications, config=config, ignore_enabled=True),
        "skills": {"groups": [{"label": "Skills", "items": skill_items}] if skill_items else []},
    }


def _merge_canonical_section_records(
    generated: Any,
    canonical: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    generated_rows = [item for item in generated if isinstance(item, dict)] if isinstance(generated, list) else []
    if not canonical:
        return generated_rows
    by_key: dict[str, dict[str, Any]] = {}
    for item in generated_rows:
        for value in (
            item.get("canonical_record_id"),
            item.get("id"),
            item.get("name"),
            item.get("company"),
            item.get("role"),
        ):
            key = str(value or "").strip().casefold()
            if key:
                by_key[key] = item
    merged: list[dict[str, Any]] = []
    for item in canonical:
        candidate = deepcopy(item)
        generated_item = next(
            (by_key.get(str(value or "").strip().casefold()) for value in (
                item.get("canonical_record_id"),
                item.get("id"),
                item.get("name"),
                item.get("company"),
                item.get("role"),
            ) if str(value or "").strip().casefold() in by_key),
            None,
        )
        if generated_item is not None:
            candidate.update({k: v for k, v in generated_item.items() if v not in (None, "", [])})
        merged.append(candidate)
    return merged


def _normalize_certifications_section(raw_sections: dict[str, Any], *, config: dict[str, Any]) -> list[dict[str, Any]]:
    certification_entries: list[dict[str, Any]] = []
    for item in _coerce_object_list(raw_sections.get("certifications")):
        certification_entries.append(
            {
                "name": str(item.get("name") or "").strip(),
                "issuer": str(item.get("issuer") or "").strip() or None,
                "year": str(item.get("year") or "").strip() or None,
                "url": str(item.get("url") or item.get("link") or "").strip() or None,
            }
        )
    return _sanitize_section_entries("certifications", certification_entries, config=config)

def _normalize_publications_section(raw_sections: dict[str, Any], *, config: dict[str, Any]) -> list[dict[str, Any]]:
    publication_entries: list[dict[str, Any]] = []
    for item in _coerce_object_list(raw_sections.get("publications")):
        publication_entries.append(
            {
                "title": str(item.get("title") or "").strip(),
                "publisher": str(item.get("publisher") or "").strip() or None,
                "year": str(item.get("year") or "").strip() or None,
            }
        )
    return _sanitize_section_entries("publications", publication_entries, config=config)

def _normalize_languages_section(raw_sections: dict[str, Any], *, config: dict[str, Any]) -> list[dict[str, Any]]:
    language_entries: list[dict[str, Any]] = []
    for item in _coerce_object_list(raw_sections.get("languages")):
        language_entries.append(
            {
                "name": str(item.get("name") or "").strip(),
                "level": str(item.get("level") or "").strip() or None,
            }
        )
    return _sanitize_section_entries("languages", language_entries, config=config)


def _normalize_structured_cv(
    raw_structured_cv: dict[str, Any],
    *,
    jd: dict[str, Any],
    evidence: list[dict[str, Any]] | None,
    profile: dict[str, Any] | None,
    config: dict[str, Any],
    fit_classification: str,
    ranking_cv_handoff: dict[str, Any] | None = None,
    content_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = build_empty_structured_cv(
        jd=jd,
        profile=profile,
        config=config,
        fit_classification=fit_classification,
    )
    raw_sections = raw_structured_cv.get("sections")
    if not isinstance(raw_sections, dict):
        raw_sections = {}
    default_sections = normalized["sections"]

    composition_mode = _is_mycvs_v1_composition_plan(content_plan, config)
    if composition_mode:
        canonical_header = deepcopy(default_sections["header"])
        canonical_profile = profile if isinstance(profile, dict) else {}
        canonical_header["title"] = str(
            canonical_profile.get("title")
            or canonical_profile.get("headline")
            or canonical_profile.get("role")
            or ""
        ).strip()
        canonical_defaults = {"header": canonical_header}
        normalized["sections"]["header"] = _normalize_header_section(
            {}, canonical_defaults, canonical_only=True
        )
    else:
        normalized["sections"]["header"] = _normalize_header_section(raw_sections, default_sections)
    normalized["sections"]["summary"] = _normalize_summary_section(raw_sections)

    canonical_sections = _canonical_profile_sections(profile, config=config) if composition_mode else {}
    normalized["sections"]["experience"] = _normalize_experience_section(raw_sections, config=config)
    normalized["sections"]["projects"] = _normalize_projects_section(raw_sections, config=config)
    normalized["sections"]["education"] = _normalize_education_section(raw_sections, config=config)
    normalized["sections"]["skills"] = _normalize_skills_section(
        raw_sections,
        allowed_skill_set=None if composition_mode else _collect_allowed_skill_set(evidence or [], config=config),
        config=config,
    )

    if composition_mode:
        for key in ("experience", "projects", "education", "certifications"):
            generated = normalized["sections"].get(key)
            canonical = canonical_sections.get(key) or []
            normalized["sections"][key] = _merge_canonical_section_records(generated, canonical)
        canonical_skills = canonical_sections.get("skills") or {"groups": []}
        # Generated skills cannot expand or replace the canonical grounded skill set.
        normalized["sections"]["skills"] = canonical_skills

    normalized["sections"]["certifications"] = _normalize_certifications_section(raw_sections, config=config)
    if composition_mode:
        normalized["sections"]["certifications"] = _merge_canonical_section_records(
            normalized["sections"]["certifications"], canonical_sections.get("certifications") or []
        )
    normalized["sections"]["publications"] = _normalize_publications_section(raw_sections, config=config)
    normalized["sections"]["languages"] = _normalize_languages_section(raw_sections, config=config)
    if isinstance(ranking_cv_handoff, dict):
        normalized["ranking_cv_handoff"] = deepcopy(ranking_cv_handoff)
    if composition_mode:
        normalized["composition_plan"] = deepcopy(content_plan)

    validate_structured_cv(normalized, config=config)
    return normalized


def build_structured_generation_prompt(
    jd: dict[str, Any],
    evidence: list[dict[str, Any]],
    gap: dict[str, Any],
    template: str,
    profile: dict[str, Any] | None = None,
    *,
    config: dict[str, Any] | None = None,
    evidence_selection_summary: dict[str, Any] | None = None,
    repair_missing_sections: list[str] | None = None,
    content_plan: dict[str, Any] | None = None,
    target_sections: list[str] | None = None,
) -> str:
    structured_schema = textwrap.dedent(
        """\
        {
          "sections": {
            "header": {
              "name": "...",
              "title": "...",
              "location": null,
              "contact": {"email": null, "phone": null, "linkedin": null}
            },
            "summary": {"text": "..."},
            "experience": [{"role": "...", "company": "...", "start": null, "end": null, "location": null, "bullets": ["..."]}],
            "projects": [{"name": "...", "context": null, "bullets": ["..."]}],
            "education": [{"degree": "...", "institution": "...", "field": null, "start": null, "end": null}],
            "skills": {"groups": [{"label": "...", "items": ["..."]}]},
            "certifications": [{"name": "...", "issuer": null, "year": null}],
            "publications": [{"title": "...", "publisher": null, "year": null}],
            "languages": [{"name": "...", "level": null}]
          }
        }
        """
    )
    prompt_context = _build_generation_prompt_context(
        jd=jd,
        evidence=evidence,
        gap=gap,
        template=template,
        profile=profile,
        config=config,
        evidence_selection_summary=evidence_selection_summary,
        repair_missing_sections=repair_missing_sections,
        content_plan=content_plan,
        target_sections=target_sections,
    )
    prompt_id = get_cv_generation_structured_prompt_id(config or {})
    return render_prompt(
        prompt_id,
        {
            **prompt_context,
            "structured_schema": structured_schema,
            "output_instruction": (
                "Write only valid JSON matching the schema below. "
                "Do not add commentary. Do not wrap the JSON in markdown code fences."
            ),
        },
        replacement_text=get_prompt_replacement(
            "cv_generation_structured_write", config
        ),
    ).text


# ── prompt assembly ───────────────────────────────────────────────────────────

def build_generation_prompt(
    jd: dict[str, Any],
    evidence: list[dict[str, Any]],
    gap: dict[str, Any],
    template: str,
    profile: dict[str, Any] | None = None,
    *,
    config: dict[str, Any] | None = None,
    evidence_selection_summary: dict[str, Any] | None = None,
    repair_missing_sections: list[str] | None = None,
    content_plan: dict[str, Any] | None = None,
    target_sections: list[str] | None = None,
) -> str:
    """Assemble the full LLM prompt for CV generation.

    The prompt contains:
    - JD context (title + required skills)
    - Selected evidence items (name + skills)
    - Gap constraints (matched and missing skills)
    - The Jinja2 template string as the output format guide

    Returns a plain string suitable for sending to an LLM as a single user message.
    """
    prompt_context = _build_generation_prompt_context(
        jd=jd,
        evidence=evidence,
        gap=gap,
        template=template,
        profile=profile,
        config=config,
        evidence_selection_summary=evidence_selection_summary,
        repair_missing_sections=repair_missing_sections,
        content_plan=content_plan,
        target_sections=target_sections,
    )
    return render_prompt(
        LEGACY_MARKDOWN_PROMPT_ID,
        {
            **prompt_context,
            "output_instruction": "Write only the completed CV markdown. Do not add commentary.",
        },
    ).text


# ── template rendering ────────────────────────────────────────────────────────

def render_cv_template(
    template_str: str,
    selected_skills: list[str],
    selected_experiences: list[dict[str, Any]],
    selected_projects: list[dict[str, Any]],
    candidate: dict[str, Any],
    headline: str,
    summary: str,
    selected_education: list[dict[str, Any]] | None = None,
    selected_publications: list[dict[str, Any]] | None = None,
    selected_certifications: list[dict[str, Any]] | None = None,
    selected_languages: list[dict[str, Any]] | None = None,
) -> str:
    """Render a Jinja2 CV template with the selected evidence slots.

    Args:
        template_str:          Jinja2 template source string.
        selected_skills:       Skills to populate the Skills section.
        selected_experiences:  Experience dicts (role, company, start, end, bullets).
        selected_projects:     Project dicts (name, description).
        candidate:             Candidate metadata dict (must include ``name``).
        headline:              One-line professional headline.
        summary:               Professional summary paragraph.

    Returns the rendered markdown string.
    Raises TemplateError on rendering failure (propagated to caller).
    """
    env = Environment(loader=BaseLoader(), autoescape=False)  # noqa: S701 — output is markdown, not HTML
    tmpl = env.from_string(template_str)
    return tmpl.render(
        selected_skills=selected_skills,
        selected_experiences=selected_experiences,
        selected_projects=selected_projects,
        selected_education=selected_education or [],
        selected_publications=selected_publications or [],
        selected_certifications=selected_certifications or [],
        selected_languages=selected_languages or [],
        candidate=candidate,
        headline=headline,
        summary=summary,
    )

def _collect_allowed_skill_set(
    evidence: list[dict[str, Any]],
    *,
    config: dict[str, Any] | None,
) -> set[str]:
    allowed_skill_set: set[str] = set()
    for item in evidence:
        for raw_skill in item.get("skills") or []:
            text = str(raw_skill or "").strip()
            if not text:
                continue
            canonical = canonicalize_skill(text, config or {})
            if canonical:
                allowed_skill_set.add(canonical)
    return allowed_skill_set

def _normalize_cv_markdown(markdown: str) -> str:
    """Deterministically normalize rendered CV markdown formatting."""
    text = str(markdown or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?m)^\s*[\*\u2022]\s+", "- ", text)
    text = re.sub(r"(?m)^\s*-\s{2,}", "- ", text)
    raw_lines = [line.rstrip() for line in text.split("\n")]
    lines: list[str] = []
    for idx, line in enumerate(raw_lines):
        stripped = line.strip()
        if stripped:
            lines.append(line)
            continue
        prev_nonempty = ""
        next_nonempty = ""
        for prev_idx in range(idx - 1, -1, -1):
            if raw_lines[prev_idx].strip():
                prev_nonempty = raw_lines[prev_idx].strip()
                break
        for next_idx in range(idx + 1, len(raw_lines)):
            if raw_lines[next_idx].strip():
                next_nonempty = raw_lines[next_idx].strip()
                break
        # Drop empty lines between adjacent list bullets for compact, consistent lists.
        if prev_nonempty.startswith("- ") and next_nonempty.startswith("- "):
            continue
        lines.append(line)

    normalized_lines: list[str] = []
    previous_was_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank:
            if not previous_was_blank:
                normalized_lines.append("")
            previous_was_blank = True
            continue
        normalized_lines.append(line)
        previous_was_blank = False
    text = "\n".join(normalized_lines).strip()
    text = re.sub(r"\n{2,}(## )", r"\n\n\1", text)
    text = re.sub(r"(?<!\n)\n(## )", r"\n\n\1", text)
    return text.strip() + "\n"


def _normalize_mycvs_v1_text(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).strip() + "\n"


def _mycvs_line(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\r", " ").replace("\n", " ")).strip()


def _mycvs_list(value: Any) -> list[str]:
    if isinstance(value, (str, int, float)):
        value = [value]
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(_mycvs_line(item) for item in value if _mycvs_line(item)))


def _append_mycvs_bullets(lines: list[str], value: Any) -> None:
    bullets = [bullet for bullet in _mycvs_list(value) if not _is_placeholder_token(bullet)]
    if not bullets:
        return
    if lines and lines[-1] != "":
        lines.append("")
    lines.extend(f"- {bullet}" for bullet in bullets)
    lines.append("")


def _mycvs_handoff_context(structured_cv: dict[str, Any]) -> tuple[dict[str, Any], str]:
    handoff = next(
        (
            structured_cv.get(key)
            for key in ("handoff", "ranking_handoff", "ranking_cv_handoff")
            if structured_cv.get(key) not in (None, "")
        ),
        {},
    )
    handoff_mapping = handoff if isinstance(handoff, dict) else {}

    def first_value(*keys: str) -> Any:
        for key in keys:
            if structured_cv.get(key) not in (None, ""):
                return structured_cv[key]
            if handoff_mapping.get(key) not in (None, ""):
                return handoff_mapping[key]
        return None

    fingerprint = first_value("handoff_fingerprint", "fingerprint", "identity", "checksum")
    if isinstance(fingerprint, dict):
        fingerprint = fingerprint.get("sha256") or fingerprint.get("value")
    if not str(fingerprint or "").strip() and handoff_mapping:
        fingerprint = _stable_render_fingerprint(handoff_mapping)
    fingerprint = _mycvs_line(fingerprint)
    if not fingerprint or ";" in fingerprint or "-->" in fingerprint:
        raise ValueError("mycvs_v1 requires a safe ranking handoff identity")
    context = {
        "job_id": first_value("job_id", "job_identifier", "job_url"),
        "profile_revision": first_value("profile_revision", "candidate_profile_revision"),
        "score_status": first_value("score_status"),
        "gaps": first_value("confirmed_gaps", "gaps"),
        "unknowns": first_value("unknowns", "confirmed_unknowns"),
    }
    return context, fingerprint


def _mycvs_source_ids(item: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("source_ids", "evidence_ids", "source_refs", "evidence_refs"):
        raw = item.get(key)
        if isinstance(raw, dict):
            raw = list(raw.keys())
        values.extend(_mycvs_list(raw))
    return list(dict.fromkeys(values))


def _mycvs_sources(structured_cv: dict[str, Any], experience: list[dict[str, Any]]) -> list[dict[str, str]]:
    raw_sources = structured_cv.get("sources")
    if raw_sources is None:
        raw_sources = structured_cv.get("source_references")
    if isinstance(raw_sources, dict):
        raw_sources = [{"source_id": key, "url": value} for key, value in raw_sources.items()]
    sources: list[dict[str, str]] = []
    for raw in list(raw_sources or []):
        if isinstance(raw, str):
            source_id, url, title = _mycvs_line(raw), "", ""
        elif isinstance(raw, dict):
            source_id = _mycvs_line(raw.get("source_id") or raw.get("evidence_id") or raw.get("id"))
            url = _mycvs_line(raw.get("url") or raw.get("link") or raw.get("source_url"))
            title = _mycvs_line(raw.get("title") or raw.get("label"))
        else:
            continue
        if not source_id:
            raise ValueError("mycvs_v1 sources require stable source identifiers")
        sources.append({"source_id": source_id, "url": url, "title": title})
    known_ids = {item["source_id"] for item in sources}
    for item in experience:
        for source_id in _mycvs_source_ids(item):
            if source_id not in known_ids:
                sources.append({"source_id": source_id, "url": "", "title": ""})
                known_ids.add(source_id)
    return sources


def _mycvs_url_is_valid(url: str) -> bool:
    parsed = urlsplit(url)
    return bool(
        url
        and "\n" not in url
        and "\r" not in url
        and parsed.scheme in {"http", "https"}
        and parsed.netloc
        and not parsed.username
        and not parsed.password
    )


def _mycvs_link_is_valid(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.scheme in {"mailto", "tel"}:
        return bool(parsed.path) and "\r" not in url and "\n" not in url
    return _mycvs_url_is_valid(url)


def _mycvs_contact_link(icon: str, label: str, target: str) -> str:
    return f'<span class="iconify" data-icon="{icon}"></span> [{label}](<{target}>)'


def _serialize_mycvs_v1_composed(structured_cv: dict[str, Any]) -> str:
    """Serialize a composition-plan-backed CV using the myCVs v1 grammar."""
    sections = structured_cv["sections"]
    header = sections["header"]
    candidate_name = _mycvs_line(header.get("name"))
    if not candidate_name or _is_placeholder_token(candidate_name):
        raise ValueError("mycvs_v1 requires a canonical candidate name")
    context, handoff = _mycvs_handoff_context(structured_cv)
    lines = ["---", "---", "", f"# {candidate_name}"]

    contact = header.get("contact") if isinstance(header.get("contact"), dict) else {}
    contact_values = []
    for key in ("email", "phone", "linkedin", "github"):
        value = _mycvs_line(contact.get(key))
        if not value or _is_placeholder_token(value):
            continue
        if key == "email":
            contact_values.append(_mycvs_contact_link("tabler:mail", value, f"mailto:{value}"))
        elif key == "phone":
            contact_values.append(_mycvs_contact_link("tabler:phone", value, f"tel:{re.sub(r'[^+0-9]', '', value)}"))
        else:
            target = value if _mycvs_url_is_valid(value) else f"https://{value}"
            if not _mycvs_url_is_valid(target):
                raise ValueError(f"mycvs_v1 {key} URL is not validated")
            icon = "tabler:brand-linkedin" if key == "linkedin" else "tabler:brand-github"
            contact_values.append(_mycvs_contact_link(icon, value, target))
    location = _mycvs_line(header.get("location"))
    if location and not _is_placeholder_token(location):
        contact_values.append(f'<span class="iconify" data-icon="ic:outline-location-on"></span> {location}')
    if contact_values:
        lines.extend(["", "  : ".join(contact_values)])

    summary = _mycvs_line((sections.get("summary") or {}).get("text"))
    if not summary or _is_placeholder_token(summary):
        raise ValueError("mycvs_v1 requires a grounded Summary")
    lines.extend(["", "## Summary", summary])

    def add_heading(heading: str) -> None:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(f"## {heading}")

    education = [
        item for item in sections.get("education", [])
        if isinstance(item, dict) and any(not _is_placeholder_token(item.get(key)) for key in ("degree", "institution", "field", "start", "end", "details"))
    ]
    if education:
        add_heading("Education")
        for item in education:
            degree = _mycvs_line(item.get("degree"))
            institution = _mycvs_line(item.get("institution"))
            field = _mycvs_line(item.get("field"))
            title = " - ".join(value for value in (degree, field) if value and not _is_placeholder_token(value))
            if not title:
                title = institution
            if not title:
                continue
            lines.append(f"**{title}**")
            if institution and not _is_placeholder_token(institution):
                lines.append(f"  : **{institution}**")
            period = " - ".join(value for value in (_mycvs_line(item.get("start")), _mycvs_line(item.get("end"))) if value)
            if period:
                lines.append(f"  : **{period}**")
            details = _mycvs_line(item.get("details"))
            if details and not _is_placeholder_token(details):
                lines.extend(["", details])

    experience = [
        item for item in sections.get("experience", [])
        if isinstance(item, dict) and any(not _is_placeholder_token(item.get(key)) for key in ("role", "company", "location", "start", "end", "overview"))
    ]
    if experience:
        add_heading("Experience")
        for index, item in enumerate(experience):
            if index and lines and lines[-1] != "":
                lines.append("")
            role = _mycvs_line(item.get("role"))
            company = _mycvs_line(item.get("company"))
            title = " - ".join(value for value in (role, company) if value and not _is_placeholder_token(value))
            if not title:
                continue
            lines.append(f"**{title}**")
            location = _mycvs_line(item.get("location"))
            period = " - ".join(value for value in (_mycvs_line(item.get("start")), _mycvs_line(item.get("end"))) if value)
            if location:
                lines.append(f"  : **{location}**")
            if period:
                lines.append(f"  : **{period}**")
            overview = _mycvs_line(item.get("overview"))
            if overview and not _is_placeholder_token(overview):
                lines.extend(["", overview])
            _append_mycvs_bullets(lines, item.get("bullets"))

    projects = [
        item for item in sections.get("projects", [])
        if isinstance(item, dict) and any(not _is_placeholder_token(item.get(key)) for key in ("name", "context", "url", "start", "end", "overview"))
    ]
    if projects:
        add_heading("Projects")
        for index, item in enumerate(projects):
            if index and lines and lines[-1] != "":
                lines.append("")
            name = _mycvs_line(item.get("name"))
            if not name or _is_placeholder_token(name):
                continue
            url = _mycvs_line(item.get("url"))
            if url:
                if not _mycvs_url_is_valid(url):
                    raise ValueError(f"mycvs_v1 project URL is not validated: {url!r}")
                name = f"[GitHub icon: {name}](<{url}>)"
            lines.append(f"**{name}**")
            context_text = _mycvs_line(item.get("context"))
            if context_text:
                lines.append(f"  : **{context_text}**")
            period = " - ".join(value for value in (_mycvs_line(item.get("start")), _mycvs_line(item.get("end"))) if value)
            if period:
                lines.append(f"  : **{period}**")
            overview = _mycvs_line(item.get("overview"))
            if overview and not _is_placeholder_token(overview):
                lines.extend(["", overview])
            _append_mycvs_bullets(lines, item.get("bullets"))

    certificates = [
        item for item in sections.get("certifications", [])
        if isinstance(item, dict) and any(not _is_placeholder_token(item.get(key)) for key in ("name", "issuer", "year", "url", "details"))
    ]
    if certificates:
        add_heading("Certificates")
        for item in certificates:
            name = _mycvs_line(item.get("name"))
            if not name or _is_placeholder_token(name):
                continue
            url = _mycvs_line(item.get("url"))
            if url:
                if not _mycvs_url_is_valid(url):
                    raise ValueError(f"mycvs_v1 certificate URL is not validated: {url!r}")
                name = f"[{name}](<{url}>)"
            lines.append(f"**{name}**")
            issuer = _mycvs_line(item.get("issuer"))
            year = _mycvs_line(item.get("year"))
            if issuer:
                lines.append(f"  : **{issuer}**")
            if year:
                lines.append(f"  : **{year}**")
            details = _mycvs_line(item.get("details"))
            if details and not _is_placeholder_token(details):
                lines.extend(["", details])

    skill_groups = [group for group in list((sections.get("skills") or {}).get("groups") or []) if isinstance(group, dict)]
    skill_groups = [group for group in skill_groups if _mycvs_list(group.get("items"))]
    if skill_groups:
        add_heading("Skills")
        for group in skill_groups:
            label = _mycvs_line(group.get("label"))
            items = _mycvs_list(group.get("items"))
            if label and items:
                lines.append(f"**{label}:** {', '.join(items)}")

    sources = _mycvs_sources(structured_cv, experience)
    audit_payload = structured_cv.get("composition_plan", {}).get("audit_metadata") if isinstance(structured_cv.get("composition_plan"), dict) else None
    if not isinstance(audit_payload, dict):
        audit_payload = {
            "job_id": _mycvs_line(context["job_id"]),
            "profile_revision": _mycvs_line(context["profile_revision"]),
            "score_status": _mycvs_line(context["score_status"]),
            "gaps": _mycvs_list(context["gaps"]),
            "unknowns": _mycvs_list(context["unknowns"]),
            "sources": sources,
        }
    else:
        audit_payload = deepcopy(audit_payload)
        audit_payload.setdefault("sources", sources)
    audit_json = json.dumps(audit_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if "-->" in audit_json:
        raise ValueError("mycvs_v1 audit metadata contains an unsafe comment delimiter")
    lines.extend(["", f"<!-- mycvs_v1_audit: {audit_json} -->"])
    payload = _normalize_mycvs_v1_text("\n".join(lines))
    checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return payload + f"<!-- mycvs_v1: schema=mycvs_v1; content_sha256={checksum}; handoff={handoff} -->\n"


def serialize_mycvs_v1(structured_cv: dict[str, Any]) -> str:
    """Serialize the canonical intermediate CV model into deterministic myCVs Markdown."""
    validate_structured_cv(structured_cv)
    if _is_mycvs_v1_composition_plan(structured_cv.get("composition_plan")):
        return _serialize_mycvs_v1_composed(structured_cv)
    sections = structured_cv["sections"]
    header = sections["header"]
    candidate_name = _mycvs_line(header.get("name"))
    if not candidate_name or _is_placeholder_token(candidate_name):
        raise ValueError("mycvs_v1 requires a canonical candidate name")
    context, handoff = _mycvs_handoff_context(structured_cv)
    experience = [item for item in sections.get("experience", []) if isinstance(item, dict)]
    sources = _mycvs_sources(structured_cv, experience)
    source_ids = {item["source_id"] for item in sources}
    contact = header.get("contact") if isinstance(header.get("contact"), dict) else {}
    contact_lines: list[str] = []
    email = _mycvs_line(contact.get("email"))
    phone = _mycvs_line(contact.get("phone"))
    linkedin = _mycvs_line(contact.get("linkedin"))
    github = _mycvs_line(contact.get("github"))
    location = _mycvs_line(header.get("location"))
    if email or phone or linkedin:
        contact_items: list[str] = []
        if email:
            contact_items.append(_mycvs_contact_link("tabler:mail", email, f"mailto:{email}"))
        if phone:
            phone_target = re.sub(r"[^+0-9]", "", phone)
            contact_items.append(_mycvs_contact_link("tabler:phone", phone, f"tel:{phone_target}"))
        if linkedin:
            linkedin_target = linkedin if _mycvs_url_is_valid(linkedin) else f"https://{linkedin}"
            if not _mycvs_url_is_valid(linkedin_target):
                raise ValueError("mycvs_v1 LinkedIn URL is not validated")
            contact_items.append(_mycvs_contact_link("tabler:brand-linkedin", linkedin, linkedin_target))
        contact_lines.append("\n  : ".join(contact_items))
    if github or location:
        contact_items = []
        if github:
            github_target = github if _mycvs_url_is_valid(github) else f"https://{github}"
            if not _mycvs_url_is_valid(github_target):
                raise ValueError("mycvs_v1 GitHub URL is not validated")
            contact_items.append(_mycvs_contact_link("tabler:brand-github", github, github_target))
        if location:
            contact_items.append(f'<span class="iconify" data-icon="ic:outline-location-on"></span> {location}')
        contact_lines.append("\n  : ".join(contact_items))

    lines = ["---", "---", "", f"# {candidate_name}"]
    if contact_lines:
        lines.extend(["", *contact_lines])
    review_notice = structured_cv.get("artifact_review")
    if isinstance(review_notice, dict) and review_notice.get("required") is True:
        reason = _mycvs_line(review_notice.get("reason")) or "Evidence or validation requires human follow-up."
        lines.extend(
            [
                "",
                "> **REVIEW REQUIRED - NOT APPROVED FOR SUBMISSION**",
                f"> {reason}",
            ]
        )
    summary = _mycvs_line((sections.get("summary") or {}).get("text"))
    if not summary or _is_placeholder_token(summary):
        raise ValueError("mycvs_v1 requires a grounded Summary")
    lines.extend(["", "## Summary", summary])

    def add_heading(heading: str) -> None:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(f"## {heading}")

    education = [
        item for item in sections.get("education", [])
        if isinstance(item, dict)
        and any(not _is_placeholder_token(item.get(key)) for key in ("degree", "institution", "field", "start", "end", "details"))
    ]
    if education:
        add_heading("Education")
        for item in education:
            degree = _mycvs_line(item.get("degree"))
            institution = _mycvs_line(item.get("institution"))
            field = _mycvs_line(item.get("field"))
            title = " - ".join(value for value in (degree, field) if value and not _is_placeholder_token(value)) or institution
            if not title:
                continue
            lines.append(f"**{title}**")
            if institution and not _is_placeholder_token(institution):
                lines.append(f"  : **{institution}**")
            period = " - ".join(value for value in (_mycvs_line(item.get("start")), _mycvs_line(item.get("end"))) if value)
            if period:
                lines.append(f"  : **{period}**")
            details = _mycvs_line(item.get("details"))
            if details and not _is_placeholder_token(details):
                lines.extend(["", details])

    experience = [
        item for item in sections.get("experience", [])
        if isinstance(item, dict)
        and any(not _is_placeholder_token(item.get(key)) for key in ("role", "company", "location", "start", "end", "overview", "bullets"))
    ]
    if experience:
        add_heading("Experience")
        for index, item in enumerate(experience):
            if index and lines and lines[-1] != "":
                lines.append("")
            role = _mycvs_line(item.get("role"))
            company = _mycvs_line(item.get("company"))
            title = " - ".join(value for value in (role, company) if value and not _is_placeholder_token(value))
            if not title:
                continue
            refs = _mycvs_source_ids(item)
            if source_ids and not refs:
                raise ValueError(f"mycvs_v1 experience item lacks source evidence: {title}")
            lines.append(f"**{title}**")
            location = _mycvs_line(item.get("location"))
            period = " - ".join(part for part in (_mycvs_line(item.get("start")), _mycvs_line(item.get("end"))) if part)
            if location:
                lines.append(f"  : **{location}**")
            if period:
                lines.append(f"  : **{period}**")
            overview = _mycvs_line(item.get("overview"))
            if overview and not _is_placeholder_token(overview):
                lines.extend(["", overview])
            _append_mycvs_bullets(lines, item.get("bullets"))

    projects = [
        item for item in sections.get("projects", [])
        if isinstance(item, dict)
        and any(not _is_placeholder_token(item.get(key)) for key in ("name", "context", "url", "start", "end", "overview", "bullets"))
    ]
    if projects:
        add_heading("Projects")
        for index, item in enumerate(projects):
            if index and lines and lines[-1] != "":
                lines.append("")
            name = _mycvs_line(item.get("name"))
            if not name or _is_placeholder_token(name):
                continue
            url = _mycvs_line(item.get("url"))
            if url:
                if not _mycvs_url_is_valid(url):
                    raise ValueError(f"mycvs_v1 project URL is not validated: {url!r}")
                name = f"[GitHub icon: {name}](<{url}>)"
            lines.append(f"**{name}**")
            context_text = _mycvs_line(item.get("context"))
            if context_text and not _is_placeholder_token(context_text):
                lines.append(f"  : **{context_text}**")
            period = " - ".join(value for value in (_mycvs_line(item.get("start")), _mycvs_line(item.get("end"))) if value)
            if period:
                lines.append(f"  : **{period}**")
            overview = _mycvs_line(item.get("overview"))
            if overview and not _is_placeholder_token(overview):
                lines.extend(["", overview])
            _append_mycvs_bullets(lines, item.get("bullets"))

    certificates = [
        item for item in sections.get("certifications", [])
        if isinstance(item, dict)
        and any(not _is_placeholder_token(item.get(key)) for key in ("name", "issuer", "year", "url", "details"))
    ]
    if certificates:
        add_heading("Certificates")
        for item in certificates:
            name = _mycvs_line(item.get("name"))
            if not name or _is_placeholder_token(name):
                continue
            url = _mycvs_line(item.get("url"))
            if url:
                if not _mycvs_url_is_valid(url):
                    raise ValueError(f"mycvs_v1 certificate URL is not validated: {url!r}")
                name = f"[{name}](<{url}>)"
            lines.append(f"**{name}**")
            issuer = _mycvs_line(item.get("issuer"))
            year = _mycvs_line(item.get("year"))
            if issuer and not _is_placeholder_token(issuer):
                lines.append(f"  : **{issuer}**")
            if year and not _is_placeholder_token(year):
                lines.append(f"  : **{year}**")
            details = _mycvs_line(item.get("details"))
            if details and not _is_placeholder_token(details):
                lines.extend(["", details])

    skill_groups = [group for group in list((sections.get("skills") or {}).get("groups") or []) if isinstance(group, dict)]
    skill_groups = [group for group in skill_groups if _mycvs_list(group.get("items"))]
    if skill_groups:
        add_heading("Skills")
        for group in skill_groups:
            label = _mycvs_line(group.get("label"))
            items = _mycvs_list(group.get("items"))
            if label and items:
                lines.append(f"**{label}:** {', '.join(items)}")

    audit_payload = {
        "job_id": _mycvs_line(context["job_id"]),
        "profile_revision": _mycvs_line(context["profile_revision"]),
        "score_status": _mycvs_line(context["score_status"]),
        "gaps": _mycvs_list(context["gaps"]),
        "unknowns": _mycvs_list(context["unknowns"]),
        "sources": sources,
        "artifact_review": {
            "required": bool(isinstance(review_notice, dict) and review_notice.get("required") is True),
            "reason": _mycvs_line(review_notice.get("reason")) if isinstance(review_notice, dict) else "",
        },
    }
    for source in sources:
        source_url = source["url"]
        if source_url and not _mycvs_url_is_valid(source_url):
            raise ValueError(f"mycvs_v1 source URL is not validated: {source_url!r}")
    audit_json = json.dumps(audit_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if "-->" in audit_json:
        raise ValueError("mycvs_v1 audit metadata contains an unsafe comment delimiter")
    lines.extend(["", f"<!-- mycvs_v1_audit: {audit_json} -->"])
    payload = _normalize_mycvs_v1_text("\n".join(lines))
    checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return payload + f"<!-- mycvs_v1: schema=mycvs_v1; content_sha256={checksum}; handoff={handoff} -->\n"


def validate_mycvs_v1_markdown(
    markdown: str,
    *,
    expected_handoff: str | None = None,
    content_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate myCVs Markdown and return its normalized checksum metadata."""
    text = str(markdown or "")
    errors: list[str] = []
    if "\r" in text:
        errors.append("line endings must be LF")
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        errors.append("content must be UTF-8")
    if any(line != line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")):
        errors.append("trailing whitespace is not allowed")
    metadata_matches = list(re.finditer(r"^<!-- mycvs_v1:.* -->$", text, re.MULTILINE))
    if len(metadata_matches) != 1:
        errors.append("exactly one mycvs_v1 metadata block is required")
        metadata_match = None
        metadata_span = None
    else:
        metadata_span = metadata_matches[0]
        metadata_match = MYCVS_V1_METADATA_LINE_RE.fullmatch(metadata_span.group(0))
        if metadata_match is None:
            errors.append("invalid mycvs_v1 metadata block")
    if metadata_match is not None:
        if text[metadata_span.end():].strip():
            errors.append("metadata block must be final")
        payload = _normalize_mycvs_v1_text(text[:metadata_span.start()])
        checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if checksum != metadata_match.group(1):
            errors.append("content checksum mismatch")
        handoff = metadata_match.group(2).strip()
        if expected_handoff is not None and handoff != _mycvs_line(expected_handoff):
            errors.append("handoff identity mismatch")
    else:
        payload, handoff = text, ""
    payload_lines = payload.splitlines()
    for index, line in enumerate(payload_lines):
        if not line.startswith("- "):
            continue
        previous = payload_lines[index - 1] if index else ""
        following = payload_lines[index + 1] if index + 1 < len(payload_lines) else ""
        if previous and not previous.startswith("- "):
            errors.append("bullet list must start after a blank line")
        if following and not following.startswith("- "):
            errors.append("bullet list must end before a blank line")
    strict_composition = payload.startswith("---\n---\n")
    visible_payload = "\n".join(
        line for line in payload_lines if not MYCVS_V1_AUDIT_LINE_RE.fullmatch(line)
    )
    if strict_composition:
        visible_lower = visible_payload.casefold()
        visible_tokens = (
            "not provided",
            "none provided",
            "n/a",
            "unknown",
            "evidence:",
            "evidence_id",
            "requirement_id",
            "claim_id",
            "fingerprint",
            "provenance",
            "selected_support",
        )
        if any(token in visible_lower for token in visible_tokens):
            errors.append("recruiter-facing CV contains a placeholder or provenance token")
        if not payload_lines or payload_lines[:2] != ["---", "---"]:
            errors.append("mycvs_v1 composition requires empty YAML front matter")
    headings = [(match.group(1), match.group(2).strip()) for line in payload_lines if (match := re.match(r"^(#{1,6})[ \t]+(.+?)\s*$", line))]
    expected_headings = [("#", payload_lines[3][2:].strip() if strict_composition and len(payload_lines) > 3 and payload_lines[3].startswith("# ") else payload_lines[0][2:].strip() if payload_lines and payload_lines[0].startswith("# ") else ""), *[("##", heading) for heading in MYCVS_V1_HEADINGS]]
    if strict_composition:
        allowed = [("##", heading) for heading in MYCVS_V1_HEADINGS]
        actual_sections = headings[1:]
        if (
            not expected_headings[0][1]
            or any(item not in allowed for item in actual_sections)
            or len(actual_sections) != len(set(actual_sections))
            or actual_sections != sorted(actual_sections, key=lambda item: allowed.index(item))
        ):
            errors.append("headings must follow the source-driven mycvs_v1 order")
        if ("##", "Summary") not in actual_sections:
            errors.append("Summary is mandatory")
        if any(line.startswith("  :") and not re.match(r"^  : .+", line) for line in payload_lines):
            errors.append("definition-list rows must use '  : ' grammar")
    elif headings != expected_headings or not expected_headings[0][1]:
        errors.append("headings must match the fixed mycvs_v1 order")
    for link in re.findall(r"\[[^\]]+\]\((?:<([^>\r\n]+)>|([^\)\r\n]+))\)", payload):
        url = link[0] or link[1]
        if not _mycvs_link_is_valid(url):
            errors.append(f"unsupported source URL: {url!r}")
    audit_matches = [match for line in payload_lines if (match := MYCVS_V1_AUDIT_LINE_RE.fullmatch(line))]
    audit_payload: dict[str, Any] | None = None
    if len(audit_matches) != 1:
        errors.append("exactly one mycvs_v1 audit block is required")
    else:
        try:
            parsed_audit = json.loads(audit_matches[0].group(1))
            if not isinstance(parsed_audit, dict):
                raise ValueError
            audit_payload = parsed_audit
        except (TypeError, ValueError, json.JSONDecodeError):
            errors.append("invalid mycvs_v1 audit block")
    required_audit_keys = ("job_id", "profile_revision", "score_status", "gaps", "unknowns", "sources")
    if audit_payload is not None and not all(key in audit_payload for key in required_audit_keys):
        errors.append("audit block must include job, profile, score, gaps, unknowns, and sources")
    if audit_payload is not None:
        for source in audit_payload.get("sources") or []:
            if not isinstance(source, dict) or not str(source.get("source_id") or "").strip():
                errors.append("audit sources require stable source identifiers")
                continue
            source_url = str(source.get("url") or "").strip()
            if source_url and not _mycvs_url_is_valid(source_url):
                errors.append(f"unsupported audit source URL: {source_url!r}")
    if not handoff:
        errors.append("handoff identity is required")
    if strict_composition and isinstance(content_plan, dict):
        plan_for_hash = deepcopy(content_plan)
        expected_plan_fingerprint = str(plan_for_hash.pop("plan_fingerprint", "") or "").strip()
        plan_for_hash.pop("content_fingerprint", None)
        if expected_plan_fingerprint:
            actual_plan_fingerprint = hashlib.sha256(
                json.dumps(plan_for_hash, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
            ).hexdigest()
            if actual_plan_fingerprint != expected_plan_fingerprint:
                errors.append("composition plan fingerprint mismatch")
        selected_ids = {
            str(item.get("evidence_id") or item.get("claim_id") or "").strip()
            for item in list(content_plan.get("selected_job_support") or [])
            if isinstance(item, dict) and str(item.get("evidence_id") or item.get("claim_id") or "").strip()
        }
        claims = list(content_plan.get("supported_job_claims") or content_plan.get("approved_claims") or [])
        for claim in claims:
            if not isinstance(claim, dict):
                errors.append("supported job claims must be objects")
                continue
            claim_id = str(claim.get("claim_id") or claim.get("evidence_id") or "").strip()
            if not claim_id or (selected_ids and claim_id not in selected_ids):
                errors.append("supported job claim references unknown evidence")
            if not list(claim.get("supports_requirements") or []):
                errors.append("supported job claim lacks requirement references")
        handoff_identity = str(content_plan.get("ranking_handoff_identity") or "").strip()
        if expected_handoff is not None and handoff_identity and handoff_identity != _mycvs_line(expected_handoff):
            errors.append("composition plan ranking handoff identity mismatch")
        visible_ids = selected_ids | {
            str(item.get("claim_id") or item.get("evidence_id") or "").strip()
            for item in claims
            if isinstance(item, dict) and str(item.get("claim_id") or item.get("evidence_id") or "").strip()
        }
        if any(identifier.casefold() in visible_payload.casefold() for identifier in visible_ids):
            errors.append("recruiter-facing CV contains an evidence identifier")
        baseline = content_plan.get("records_selected_for_render") or content_plan.get("baseline_profile_records") or {}
        section_map = {
            "education": "education",
            "experiences": "experience",
            "experience": "experience",
            "projects": "projects",
            "certifications": "certifications",
        }
        for source_key, section_key in section_map.items():
            records = baseline.get(source_key) if isinstance(baseline, dict) else None
            if not isinstance(records, list):
                continue
            for record in records:
                if not isinstance(record, dict):
                    continue
                identity_values = (
                    record.get("name"),
                    record.get("title"),
                    record.get("degree"),
                    record.get("role"),
                    record.get("company"),
                    record.get("institution"),
                    record.get("issuer"),
                )
                identity = next(
                    (
                        str(value).strip()
                        for value in identity_values
                        if str(value or "").strip() and not _is_placeholder_token(value)
                    ),
                    "",
                )
                if identity and identity.casefold() not in visible_payload.casefold():
                    errors.append(f"canonical {section_key} record is missing: {identity}")
    if errors:
        raise ValueError("mycvs_v1 validation failed: " + "; ".join(dict.fromkeys(errors)))
    return {"valid": True, "content_sha256": metadata_match.group(1), "handoff": handoff}


render_mycvs_v1_markdown = serialize_mycvs_v1
validate_mycvs_v1 = validate_mycvs_v1_markdown


# ── LLM generation (integration) ─────────────────────────────────────────────

def _resolve_template_path(config: dict[str, Any]) -> str:
    """Resolve the CV template path from the preset-based config.

    Priority:
    1. config["_template_path"] — test shim (used by generate_cv test fixtures)
    2. cv_presets.get_template_path(config["cv"]["preset"])
    3. Fallback to flat cv_template_path for legacy compatibility
    """
    if "_template_path" in config:
        return str(config["_template_path"])
    cv_cfg = config.get("cv") or {}
    preset = str(cv_cfg.get("preset", ""))
    if preset:
        from fitcv.cv_presets import get_template_path

        return get_template_path(preset)
    return str(config.get("cv_template_path", "templates/cv_template.md"))


def _inject_review_notice(markdown: str, structured_cv: dict[str, Any]) -> str:
    review_notice = structured_cv.get("artifact_review")
    if not isinstance(review_notice, dict) or review_notice.get("required") is not True:
        return markdown
    if "REVIEW REQUIRED - NOT APPROVED FOR SUBMISSION" in markdown:
        return markdown
    reason = str(review_notice.get("reason") or "Evidence or validation requires human follow-up.").strip()
    lines = markdown.splitlines()
    insert_at = next((index + 1 for index, line in enumerate(lines) if line.startswith("# ")), 0)
    lines[insert_at:insert_at] = ["", "> **REVIEW REQUIRED - NOT APPROVED FOR SUBMISSION**", f"> {reason}", ""]
    return "\n".join(lines).rstrip() + "\n"


def render_cv_markdown(structured_cv: dict[str, Any], config: dict[str, Any]) -> str:
    """Render markdown from a validated structured CV document."""
    if get_cv_renderer_strategy(config) == "mycvs_v1":
        return serialize_mycvs_v1(structured_cv)
    import pathlib

    structured_cv = deepcopy(structured_cv)
    sections = structured_cv.get("sections")
    if isinstance(sections, dict):
        for section_key in ("experience", "projects", "education", "certifications", "publications", "languages"):
            section_items = sections.get(section_key)
            if not isinstance(section_items, list):
                continue
            sections[section_key] = _sanitize_section_entries(
                section_key,
                [item for item in section_items if isinstance(item, dict)],
                config=config,
            )
    validate_structured_cv(structured_cv, config=config)
    template_path = _resolve_template_path(config)
    template_str = pathlib.Path(template_path).read_text(encoding="utf-8")
    enabled_section_names = _get_enabled_section_names(config)
    template_str = _filter_template_by_enabled_sections(template_str, enabled_section_names)
    sections = structured_cv["sections"]
    header = sections["header"]
    flattened_skills = [
        item
        for group in sections["skills"]["groups"]
        for item in group["items"]
    ]
    selected_projects: list[dict[str, Any]] = []
    for project in sections["projects"]:
        context = str(project.get("context") or "").strip()
        bullets = [str(bullet).strip() for bullet in (project.get("bullets") or []) if str(bullet).strip()]
        description_lines: list[str] = []
        if context:
            description_lines.append(context)
        if bullets:
            description_lines.extend(f"- {bullet}" for bullet in bullets)
        selected_projects.append(
            {
                "name": project.get("name"),
                "description": "\n".join(description_lines).strip(),
            }
        )
    selected_education = [
        {
            "degree": item.get("degree"),
            "institution": item.get("institution"),
            "field": item.get("field"),
            "start": item.get("start"),
            "end": item.get("end"),
        }
        for item in sections["education"]
    ]
    selected_publications = [
        {
            "title": item.get("title"),
            "publisher": item.get("publisher"),
            "year": item.get("year"),
        }
        for item in sections["publications"]
    ]
    selected_certifications = [
        {
            "name": item.get("name"),
            "issuer": item.get("issuer"),
            "year": item.get("year"),
        }
        for item in sections["certifications"]
    ]
    selected_languages = [
        {
            "name": item.get("name"),
            "level": item.get("level"),
        }
        for item in sections["languages"]
    ]
    rendered = render_cv_template(
        template_str=template_str,
        selected_skills=flattened_skills,
        selected_experiences=sections["experience"],
        selected_projects=selected_projects,
        selected_education=selected_education,
        selected_publications=selected_publications,
        selected_certifications=selected_certifications,
        selected_languages=selected_languages,
        candidate={"name": header.get("name", "")},
        headline=str(header.get("title") or ""),
        summary=str(sections["summary"].get("text") or ""),
    )
    return _inject_review_notice(_normalize_cv_markdown(rendered), structured_cv)


def _canonical_render_item_key(section: str, item: dict[str, Any]) -> str:
    section_name = str(section or "").strip().lower()
    if section_name == "languages":
        raw = str(item.get("name") or "")
    elif section_name == "projects":
        raw = " ".join(
            [
                str(item.get("name") or ""),
                str(item.get("context") or ""),
                *[str(value) for value in list(item.get("bullets") or [])],
            ]
        )
    else:
        raw = " ".join(str(value) for value in item.values())
    normalized = re.sub(r"[^a-z0-9]+", " ", raw.casefold()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return f"{section_name}:{normalized}"


def _render_config_fingerprint(config: dict[str, Any]) -> str:
    payload = {
        "cv": dict(config.get("cv") or {}),
        "cv_template_path": str(config.get("cv_template_path") or ""),
        "template_path": str(config.get("_template_path") or ""),
        "external_renderer": _external_renderer_config(config),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _template_sha256(config: dict[str, Any]) -> str | None:
    try:
        return hashlib.sha256(Path(_resolve_template_path(config)).read_bytes()).hexdigest()
    except (OSError, TypeError, ValueError):
        return None


def _external_renderer_config(config: dict[str, Any]) -> dict[str, str]:
    renderer = ((config.get("cv") or {}).get("renderer") or {})
    external = renderer.get("external") if isinstance(renderer, dict) else {}
    if not isinstance(external, dict):
        external = {}
    enabled = external.get("enabled") or os.environ.get("FITCV_MYCVS_EXTERNAL_RENDER_ENABLED")
    bundled = {
        "converter_path": _BUNDLED_MYCVS_RENDERER_DIR / "build_refined_converter_generic.py",
        "stylesheet_path": _BUNDLED_MYCVS_RENDERER_DIR / "long-dang-template.css",
        "font_regular_path": _BUNDLED_MYCVS_RENDERER_DIR / "fonts" / "Inter-Regular.ttf",
        "font_bold_path": _BUNDLED_MYCVS_RENDERER_DIR / "fonts" / "Inter-Bold.ttf",
    }
    use_bundled = str(enabled or "").strip().lower() in {"1", "true", "yes", "on"}

    def bundled_path(key: str) -> str | None:
        path = bundled[key]
        return str(path) if use_bundled and path.is_file() else None

    values = {
        "enabled": enabled,
        "converter_path": external.get("converter_path")
        or os.environ.get("FITCV_MYCVS_CONVERTER_PATH")
        or bundled_path("converter_path"),
        "stylesheet_path": external.get("stylesheet_path")
        or os.environ.get("FITCV_MYCVS_STYLESHEET_PATH")
        or bundled_path("stylesheet_path"),
        "font_regular_path": external.get("font_regular_path")
        or os.environ.get("FITCV_MYCVS_INTER_REGULAR_PATH")
        or bundled_path("font_regular_path"),
        "font_bold_path": external.get("font_bold_path")
        or os.environ.get("FITCV_MYCVS_INTER_BOLD_PATH")
        or bundled_path("font_bold_path"),
        "python_path": external.get("python_path")
        or os.environ.get("FITCV_MYCVS_PYTHON"),
        "converter_revision": external.get("converter_revision")
        or os.environ.get("FITCV_MYCVS_CONVERTER_REVISION"),
        "stylesheet_revision": external.get("stylesheet_revision")
        or os.environ.get("FITCV_MYCVS_STYLESHEET_REVISION"),
        "release_manifest_path": external.get("release_manifest_path")
        or os.environ.get("FITCV_MYCVS_RELEASE_MANIFEST_PATH")
        or str(_runtime_project_root() / "config" / "policy" / "mycvs_v1_release.json"),
    }
    return {key: str(value).strip() for key, value in values.items() if str(value or "").strip()}


def _external_release_status(external: dict[str, str]) -> tuple[bool, list[str], dict[str, Any]]:
    """Require the checked-in converter and stylesheet to match one release pin."""
    manifest_path = Path(str(external.get("release_manifest_path") or ""))
    errors: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return False, ["release manifest is missing or invalid"], {}
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "mycvs_renderer_release.v1":
        errors.append("release manifest schema is invalid")
    if manifest.get("renderer_contract_version") != "mycvs_external_render_v1":
        errors.append("release manifest renderer contract is invalid")
    for key, path_key in (("converter_revision", "converter_path"), ("stylesheet_revision", "stylesheet_path")):
        expected = str(manifest.get(key) or "").strip().lower()
        actual = _sha256_file(external.get(path_key, ""))
        if not _SHA256_PATTERN.fullmatch(expected) or actual != expected:
            errors.append(f"release manifest {key} does not match the selected asset")
    if str(manifest.get("proof_version") or "").strip() != "mycvs_external_render_v1":
        errors.append("release manifest proof version is invalid")
    return not errors, errors, manifest


def _render_visibility_expectations(
    structured_cv: dict[str, Any],
    *,
    certifications_heading: str = "Certificates",
) -> tuple[list[str], list[str]]:
    sections = structured_cv.get("sections") if isinstance(structured_cv, dict) else {}
    if not isinstance(sections, dict):
        return [], []
    expected_text: list[str] = []
    representative_records: list[str] = []
    header = sections.get("header") if isinstance(sections.get("header"), dict) else {}
    if str(header.get("name") or "").strip():
        expected_text.append(str(header["name"]).strip())
    section_names = {
        "summary": "Summary",
        "education": "Education",
        "experience": "Experience",
        "projects": "Projects",
        "certifications": certifications_heading,
        "skills": "Skills",
    }
    identity_fields = {
        "education": ("degree", "institution", "name"),
        "experience": ("role", "company", "title", "name"),
        "projects": ("name", "title"),
        "certifications": ("name", "title"),
    }
    for key, heading in section_names.items():
        value = sections.get(key)
        if value in (None, [], {}, ""):
            continue
        expected_text.append(heading)
        if key == "skills":
            groups = value.get("groups") if isinstance(value, dict) else []
            first_skill = next(
                (str(item).strip() for group in groups or [] if isinstance(group, dict) for item in group.get("items") or [] if str(item).strip()),
                "",
            )
            if first_skill:
                representative_records.append(first_skill)
            continue
        records = value if isinstance(value, list) else []
        if records and isinstance(records[0], dict):
            representative = next(
                (str(records[0].get(field)).strip() for field in identity_fields.get(key, ()) if str(records[0].get(field) or "").strip()),
                "",
            )
            if representative:
                representative_records.append(representative)
    return expected_text, representative_records


def _validate_rendered_pdf_content(
    extracted_text: str,
    structured_cv: dict[str, Any] | None,
    *,
    certifications_heading: str = "Certificates",
) -> dict[str, Any]:
    if not isinstance(structured_cv, dict):
        return {"status": "not_applicable", "expected_text_errors": [], "record_visibility_errors": []}
    visible = str(extracted_text or "").casefold()
    expected_text, representative_records = _render_visibility_expectations(
        structured_cv,
        certifications_heading=certifications_heading,
    )
    visible_for_match = _normalize_rendered_text_for_match(visible)
    def is_visible(item: str) -> bool:
        normalized = _normalize_rendered_text_for_match(item)
        if normalized in visible_for_match:
            return True
        return " " in normalized and normalized.replace(" ", "") in visible_for_match.replace(" ", "")

    expected_errors = [
        f"expected rendered text is missing: {item}" for item in expected_text if not is_visible(item)
    ]
    record_errors = [
        f"representative canonical record is not visible: {item}"
        for item in representative_records
        if not is_visible(item)
    ]
    return {
        "status": "pass" if not expected_errors and not record_errors else "fail",
        "expected_text_status": "pass" if not expected_errors else "fail",
        "expected_text_errors": expected_errors,
        "record_visibility_status": "pass" if not record_errors else "fail",
        "record_visibility_errors": record_errors,
    }


def _normalize_rendered_text_for_match(value: Any) -> str:
    """Normalize PDF extraction quirks without changing recruiter-facing text checks."""
    text = " ".join(str(value or "").casefold().split())
    return re.sub(
        r"(?<![a-z0-9])(?:[a-z0-9]\s+){2,}[a-z0-9](?![a-z0-9])",
        lambda match: re.sub(r"\s+", "", match.group(0)),
        text,
        flags=re.IGNORECASE,
    )

def _external_renderer_command(
    external: dict[str, str],
    markdown_path: Path,
    output_path: Path,
) -> list[str] | None:
    converter_path = str(external.get("converter_path") or "")
    if not converter_path:
        return None
    runtime = sys.executable
    if getattr(sys, "frozen", False):
        runtime = str(external.get("python_path") or shutil.which("python") or shutil.which("py") or "")
        if not runtime:
            return None
    return [runtime, converter_path, str(markdown_path), str(external["stylesheet_path"]), str(output_path)]

def _sha256_file(path: str) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _reference_pdf_path(config: dict[str, Any]) -> str:
    renderer = ((config.get("cv") or {}).get("renderer") or {})
    if not isinstance(renderer, dict):
        renderer = {}
    external = renderer.get("external") if isinstance(renderer.get("external"), dict) else {}
    return str(
        renderer.get("reference_pdf_path")
        or external.get("reference_pdf_path")
        or os.environ.get("FITCV_MYCVS_REFERENCE_PDF_PATH")
        or ""
    ).strip()


def _pdf_info_metrics(page_info: str) -> dict[str, Any]:
    def number(pattern: str) -> float | None:
        match = re.search(pattern, page_info, re.MULTILINE)
        return float(match.group(1)) if match else None

    pages = re.search(r"^Pages:\s+(\d+)$", page_info, re.MULTILINE)
    return {
        "pages": int(pages.group(1)) if pages else None,
        "width": number(r"^Page size:\s+([0-9.]+) x [0-9.]+ pts"),
        "height": number(r"^Page size:\s+[0-9.]+ x ([0-9.]+) pts"),
        "rotation": int(number(r"^Page rot:\s+(-?\d+)") or 0),
    }


def _pdf_font_names(font_info: str) -> set[str]:
    names: set[str] = set()
    for line in font_info.splitlines():
        if not line.strip() or line.lstrip().startswith("name ") or line.startswith("-"):
            continue
        name = line.split()[0]
        names.add(re.sub(r"^[A-Z]{6}\+", "", name))
    return names


def _pdf_layout_metrics(bbox_xml: str) -> dict[str, Any]:
    root = ET.fromstring(bbox_xml)
    page = next((node for node in root.iter() if node.tag.endswith("page")), None)
    if page is None:
        raise ValueError("pdftotext bbox output has no page")

    lines: list[dict[str, Any]] = []
    words: list[dict[str, float]] = []
    for line in (node for node in page.iter() if node.tag.endswith("line")):
        line_words = [word for word in line if word.tag.endswith("word")]
        text = " ".join(str(word.text or "") for word in line_words).strip()
        if not text:
            continue
        line_record = {
            "text": text,
            "x_min": float(line.attrib["xMin"]),
            "x_max": float(line.attrib["xMax"]),
            "y_min": float(line.attrib["yMin"]),
            "y_max": float(line.attrib["yMax"]),
            "word_starts": [float(word.attrib["xMin"]) for word in line_words],
        }
        lines.append(line_record)
        words.extend(
            {
                "x_min": float(word.attrib["xMin"]),
                "x_max": float(word.attrib["xMax"]),
                "y_min": float(word.attrib["yMin"]),
                "y_max": float(word.attrib["yMax"]),
            }
            for word in line_words
        )

    return {
        "width": float(page.attrib["width"]),
        "height": float(page.attrib["height"]),
        "lines": lines,
        "words": words,
    }


def _layout_x_anchors(layout: dict[str, Any]) -> dict[str, float]:
    """Return stable template columns, not candidate-dependent word starts."""
    width = float(layout["width"])
    lines = layout["lines"]

    def median(values: list[float]) -> float | None:
        values = sorted(values)
        if not values:
            return None
        middle = len(values) // 2
        if len(values) % 2:
            return values[middle]
        return (values[middle - 1] + values[middle]) / 2

    candidates = {
        "left": median([float(line["x_min"]) for line in lines if float(line["x_min"]) <= 24.0]),
        "project_indent": median(
            [float(line["x_min"]) for line in lines if 24.0 <= float(line["x_min"]) < 30.0]
        ),
        "bullet_indent": median(
            [float(line["x_min"]) for line in lines if 30.0 <= float(line["x_min"]) < 80.0]
        ),
        "middle": median(
            [float(line["x_min"]) for line in lines if 250.0 <= float(line["x_min"]) <= 290.0]
        ),
        "right_edge": median(
            [float(line["x_max"]) for line in lines if float(line["x_max"]) >= width - 20.0]
        ),
    }
    return {key: value for key, value in candidates.items() if value is not None}


def _validate_pdf_against_reference(
    pdf_path: Path,
    reference_path: Path,
    *,
    candidate_page_info: str,
    work_dir: Path,
) -> dict[str, Any]:
    """Compare stable template/layout facts without comparing candidate text."""
    errors: list[str] = []
    reference_info = subprocess.run(
        ["pdfinfo", str(reference_path)],
        check=True,
        capture_output=True,
        text=True,
        cwd=work_dir,
        timeout=30,
    ).stdout
    candidate_fonts = subprocess.run(
        ["pdffonts", str(pdf_path)],
        check=True,
        capture_output=True,
        text=True,
        cwd=work_dir,
        timeout=30,
    ).stdout
    reference_fonts = subprocess.run(
        ["pdffonts", str(reference_path)],
        check=True,
        capture_output=True,
        text=True,
        cwd=work_dir,
        timeout=30,
    ).stdout
    candidate_bbox = subprocess.run(
        ["pdftotext", "-bbox-layout", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
        cwd=work_dir,
        timeout=30,
    ).stdout
    reference_bbox = subprocess.run(
        ["pdftotext", "-bbox-layout", str(reference_path), "-"],
        check=True,
        capture_output=True,
        text=True,
        cwd=work_dir,
        timeout=30,
    ).stdout

    candidate_info_metrics = _pdf_info_metrics(candidate_page_info)
    reference_info_metrics = _pdf_info_metrics(reference_info)
    candidate_layout = _pdf_layout_metrics(candidate_bbox)
    reference_layout = _pdf_layout_metrics(reference_bbox)
    candidate_fonts_set = _pdf_font_names(candidate_fonts)
    reference_fonts_set = _pdf_font_names(reference_fonts)

    if candidate_info_metrics["pages"] != 1:
        errors.append("rendered PDF must contain exactly one page")
    for key in ("width", "height"):
        if (
            candidate_info_metrics[key] is None
            or reference_info_metrics[key] is None
            or abs(float(candidate_info_metrics[key]) - float(reference_info_metrics[key])) > 2.0
        ):
            errors.append("rendered PDF page size does not match the A4 reference")
            break
    if candidate_info_metrics["rotation"] != reference_info_metrics["rotation"]:
        errors.append("rendered PDF rotation does not match the reference")
    if candidate_fonts_set != reference_fonts_set:
        errors.append("rendered PDF fonts do not match the reference typography")

    candidate_lines = candidate_layout["lines"]
    reference_lines = reference_layout["lines"]
    candidate_text = [line["text"].strip() for line in candidate_lines]
    candidate_heading_sequence = [
        line["text"].strip()
        for line in candidate_lines
        if line["text"].strip() in MYCVS_V1_HEADINGS
    ]
    candidate_headings = [
        heading for heading in MYCVS_V1_HEADINGS if heading in candidate_heading_sequence
    ]
    if candidate_heading_sequence != candidate_headings:
        errors.append("rendered PDF section headings are out of order")
    reference_heading_x = {
        line["text"].strip(): line["x_min"]
        for line in reference_lines
        if line["text"].strip() in MYCVS_V1_HEADINGS
    }
    candidate_heading_x = {
        line["text"].strip(): line["x_min"]
        for line in candidate_lines
        if line["text"].strip() in MYCVS_V1_HEADINGS
    }
    for heading, x_min in candidate_heading_x.items():
        if heading in reference_heading_x and abs(x_min - reference_heading_x[heading]) > 6.0:
            errors.append(f"rendered PDF heading alignment differs for {heading}")

    if candidate_lines:
        header = candidate_lines[0]
        header_center = (header["x_min"] + header["x_max"]) / 2
        if abs(header_center - candidate_layout["width"] / 2) > 20.0:
            errors.append("rendered PDF contact header is not centered like the reference")
    page_width = candidate_layout["width"]
    page_height = candidate_layout["height"]
    if any(
        word["x_min"] < -1 or word["y_min"] < -1 or word["x_max"] > page_width + 1 or word["y_max"] > page_height + 1
        for word in candidate_layout["words"]
    ):
        errors.append("rendered PDF contains clipped or out-of-bounds text")

    reference_anchors = _layout_x_anchors(reference_layout)
    candidate_anchors = _layout_x_anchors(candidate_layout)
    for name in reference_anchors.keys() & candidate_anchors.keys():
        expected = reference_anchors[name]
        actual = candidate_anchors[name]
        if abs(actual - expected) > 12.0:
            errors.append("rendered PDF column or bullet alignment differs from the reference")
            break
    reference_bottom = max((word["y_max"] for word in reference_layout["words"]), default=0.0)
    candidate_bottom = max((word["y_max"] for word in candidate_layout["words"]), default=0.0)
    if candidate_bottom > page_height - 8.0 or candidate_bottom > reference_bottom + 12.0:
        errors.append("rendered PDF content exceeds the reference layout bounds")

    fingerprint_payload = {
        "page": {key: candidate_info_metrics[key] for key in ("pages", "width", "height", "rotation")},
        "fonts": sorted(candidate_fonts_set),
        "headings": candidate_headings,
        "heading_x": {key: round(value, 1) for key, value in sorted(candidate_heading_x.items())},
        "anchors": {key: round(value, 1) for key, value in sorted(candidate_anchors.items())},
        "bottom": round(candidate_bottom, 1),
    }
    return {
        "status": "pass" if not errors else "fail",
        "errors": list(dict.fromkeys(errors)),
        "reference_pdf_sha256": _sha256_file(str(reference_path)),
        "reference_layout_fingerprint": hashlib.sha256(
            json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "metrics": {
            "candidate_fonts": sorted(candidate_fonts_set),
            "reference_fonts": sorted(reference_fonts_set),
            "candidate_sections": candidate_headings,
            "candidate_bottom": round(candidate_bottom, 2),
            "reference_bottom": round(reference_bottom, 2),
        },
    }


def render_cv_native_acceptance(
    content: dict[str, Any] | str,
    config: dict[str, Any],
    *,
    output_dir: str | Path | None = None,
    artifact_name: str = "cv",
) -> dict[str, Any]:
    """Render exact markdown through native tools and return final proof."""
    structured_cv = content if isinstance(content, dict) else None
    markdown = render_cv_markdown(structured_cv, config) if structured_cv is not None else str(content or "")
    markdown_validation: dict[str, Any] | None = None
    if get_cv_renderer_strategy(config) == "mycvs_v1":
        markdown_validation = validate_mycvs_v1_markdown(
            markdown,
            content_plan=structured_cv.get("composition_plan") if isinstance(structured_cv, dict) else None,
        )
    external = _external_renderer_config(config)
    reference_path_value = _reference_pdf_path(config)
    reference_path = Path(reference_path_value) if reference_path_value else None
    external_requested = external.get("enabled", "").lower() in {"1", "true", "yes", "on"}
    release_pinned, release_errors, release_manifest = (
        _external_release_status(external) if external_requested else (False, [], {})
    )
    external_enabled = external_requested and release_pinned
    if external_enabled:
        required_tools = ("pdfinfo", "pdftotext")
        if reference_path is not None:
            required_tools = (*required_tools, "pdffonts")
        missing_tools = [tool for tool in required_tools if shutil.which(tool) is None]
        for key in ("converter_path", "stylesheet_path"):
            if not external.get(key) or not Path(external[key]).is_file():
                missing_tools.append(key)
        if (
            getattr(sys, "frozen", False)
            and external.get("converter_path")
            and not (external.get("python_path") or shutil.which("python") or shutil.which("py"))
        ):
            missing_tools.append("python_runtime")
    else:
        required_tools = ("pandoc", "xelatex", "pdfinfo", "pdftotext")
        if reference_path is not None:
            required_tools = (*required_tools, "pdffonts")
        missing_tools = [tool for tool in required_tools if shutil.which(tool) is None]
    base = Path(output_dir) if output_dir is not None else None
    with TemporaryDirectory(dir=str(base) if base else None) as temporary_dir:
        work_dir = Path(temporary_dir)
        markdown_path = work_dir / f"{artifact_name}.md"
        pdf_path = work_dir / f"{artifact_name}.pdf"
        markdown_path.write_text(str(markdown or ""), encoding="utf-8", newline="\n")
        proof_identity = build_render_proof_identity(structured_cv, config) if structured_cv is not None else {}
        render_status = "render_unavailable" if missing_tools else "render_failed"
        result: dict[str, Any] = {
            **proof_identity,
            "renderer_contract_version": (
                "mycvs_external_render_v1" if external_enabled
                else proof_identity.get("renderer_contract_version", NATIVE_RENDER_CONTRACT_VERSION)
            ),
            "render_status": render_status,
            "renderer_status": render_status,
            "page_count": None,
            "page_fit_status": "unresolved",
            "artifact_checksum": None,
            "template_sha256": _template_sha256(config),
            "render_config_fingerprint": _render_config_fingerprint(config),
            "content_sha256": hashlib.sha256(str(markdown or "").encode("utf-8")).hexdigest(),
            "missing_tools": missing_tools,
            "markdown_validation_status": "pass" if markdown_validation is not None else "not_applicable",
            "reference_pdf_path": str(reference_path) if reference_path is not None else None,
            "reference_layout_status": "not_configured",
            "reference_layout_errors": [],
            "expected_text_status": "not_applicable",
            "expected_text_errors": [],
            "record_visibility_status": "not_applicable",
            "record_visibility_errors": [],
            "external_renderer_requested": external_requested,
            "external_release_status": "pass" if external_enabled else ("fail" if external_requested else "not_requested"),
            "external_release_errors": release_errors,
        }
        if external_requested:
            result.update(
                {
                    "release_manifest_path": external.get("release_manifest_path"),
                    "release_manifest": release_manifest or None,
                    "converter_revision": external.get("converter_revision") or _sha256_file(external.get("converter_path", "")),
                    "stylesheet_revision": external.get("stylesheet_revision") or _sha256_file(external.get("stylesheet_path", "")),
                    "converter_input_checksum": result["content_sha256"],
                }
            )
        if missing_tools:
            return result
        if reference_path is not None and not reference_path.is_file():
            result.update(
                {
                    "render_status": "fail",
                    "page_fit_status": "fail",
                    "reference_layout_status": "fail",
                    "reference_layout_errors": ["configured reference PDF does not exist"],
                }
            )
            return result
        try:
            if external_enabled:
                converter_command = _external_renderer_command(external, markdown_path, pdf_path)
                if converter_command is None:
                    return result
                if external.get("font_regular_path"):
                    converter_command.extend(["--inter-regular", external["font_regular_path"]])
                if external.get("font_bold_path"):
                    converter_command.extend(["--inter-bold", external["font_bold_path"]])
            else:
                converter_command = ["pandoc", str(markdown_path), "-o", str(pdf_path), "--pdf-engine=xelatex"]
            subprocess.run(
                converter_command,
                check=True,
                capture_output=True,
                text=True,
                cwd=work_dir,
                timeout=120,
            )
            page_info = subprocess.run(
                ["pdfinfo", str(pdf_path)],
                check=True,
                capture_output=True,
                text=True,
                cwd=work_dir,
                timeout=30,
            ).stdout
            page_match = re.search(r"^Pages:\s+(\d+)$", page_info, re.MULTILINE)
            if page_match is None:
                return result
            page_count = int(page_match.group(1))
            extracted_text = subprocess.run(
                ["pdftotext", str(pdf_path), "-"],
                check=True,
                capture_output=True,
                text=True,
                cwd=work_dir,
                timeout=30,
            ).stdout
            checksum = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
            visibility = _validate_rendered_pdf_content(
                extracted_text,
                structured_cv,
                certifications_heading=(
                    "Certificates" if get_cv_renderer_strategy(config) == "mycvs_v1" else "Certifications"
                ),
            )
            result.update(
                {
                    "render_status": "pass",
                    "renderer_status": "rendered",
                    "page_count": page_count,
                    "page_fit_status": "pass" if page_count == 1 else "fail",
                    "artifact_checksum": checksum,
                    **visibility,
                }
            )
            if visibility["status"] == "fail":
                result["render_status"] = "fail"
                result["page_fit_status"] = "fail"
            if reference_path is not None:
                reference_validation = _validate_pdf_against_reference(
                    pdf_path,
                    reference_path,
                    candidate_page_info=page_info,
                    work_dir=work_dir,
                )
                result.update(
                    {
                        "reference_layout_status": reference_validation["status"],
                        "reference_layout_errors": reference_validation["errors"],
                        "reference_pdf_sha256": reference_validation["reference_pdf_sha256"],
                        "reference_layout_fingerprint": reference_validation["reference_layout_fingerprint"],
                        "reference_layout_metrics": reference_validation["metrics"],
                    }
                )
                if reference_validation["status"] != "pass":
                    result["render_status"] = "fail"
                    result["page_fit_status"] = "fail"
            if output_dir is not None:
                destination = Path(output_dir)
                destination.mkdir(parents=True, exist_ok=True)
                (destination / f"{artifact_name}.md").write_text(markdown_path.read_text(encoding="utf-8"), encoding="utf-8")
                (destination / f"{artifact_name}.pdf").write_bytes(pdf_path.read_bytes())
            return result
        except (OSError, subprocess.SubprocessError, ValueError):
            return result


def render_proof_matches(
    value: dict[str, Any] | None,
    config: dict[str, Any] | None = None,
    render_acceptance: dict[str, Any] | None = None,
    *,
    content_sha256: str | None = None,
    template_sha256: str | None = None,
    render_config_fingerprint: str | None = None,
) -> bool:
    if content_sha256 is not None:
        proof = value
        proof_contract_version = str((proof or {}).get("renderer_contract_version") or NATIVE_RENDER_CONTRACT_VERSION) if isinstance(proof, dict) else NATIVE_RENDER_CONTRACT_VERSION
        if proof_contract_version not in {NATIVE_RENDER_CONTRACT_VERSION, _RENDER_CONTRACT_VERSION}:
            return False
        expected = {
            "content_sha256": content_sha256,
            "template_sha256": template_sha256,
            "render_config_fingerprint": str(render_config_fingerprint or ""),
            "renderer_contract_version": proof_contract_version,
        }
    else:
        proof = render_acceptance
        if not isinstance(value, dict) or not isinstance(config, dict):
            return False
        expected = build_render_proof_identity(value, config)
    if not isinstance(proof, dict):
        return False
    return all(proof.get(key) == expected_value for key, expected_value in expected.items())


def final_artifact_acceptance_passes(
    *,
    content_valid: bool | None = None,
    render_acceptance: dict[str, Any] | None = None,
    content_acceptance: bool | None = None,
    page_fit_status: str | None = None,
) -> bool:
    if not (content_valid if content_valid is not None else content_acceptance) or not isinstance(render_acceptance, dict):
        return False
    render_status = str(render_acceptance.get("render_status") or render_acceptance.get("renderer_status") or "").strip().lower()
    return (
        render_status in {"pass", "rendered"}
        and int(render_acceptance.get("page_count") or 0) == 1
        and str(page_fit_status or render_acceptance.get("page_fit_status") or "").strip().lower() == "pass"
        and bool(re.fullmatch(r"[0-9a-f]{64}", str(render_acceptance.get("artifact_checksum") or "")))
    )


def _provenance_by_key(provenance: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    if isinstance(provenance, dict):
        provenance = provenance.get("items")
    entries: dict[str, dict[str, Any]] = {}
    for item in list(provenance or []):
        if not isinstance(item, dict):
            continue
        key = str(item.get("canonical_item_key") or "").strip()
        if key:
            entries[key] = item
    return entries


def _render_item_provenance_for(
    by_key: dict[str, dict[str, Any]],
    section: str,
    item: dict[str, Any],
) -> dict[str, Any] | None:
    exact = by_key.get(_canonical_render_item_key(section, item))
    if exact is not None:
        return exact
    name_key = f"{section}:{re.sub(r'[^a-z0-9]+', ' ', str(item.get('name') or '').casefold()).strip()}"
    return by_key.get(name_key)


def render_item_requirement_support(
    structured_cv: dict[str, Any],
    provenance: list[dict[str, Any]] | None,
) -> set[str]:
    by_key = _provenance_by_key(provenance)
    supported: set[str] = set()
    sections = structured_cv.get("sections") if isinstance(structured_cv, dict) else None
    if not isinstance(sections, dict):
        return supported
    for section in ("experience", "projects", "education", "certifications", "publications", "languages"):
        items = sections.get(section)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            metadata = _render_item_provenance_for(by_key, section, item)
            if isinstance(metadata, dict):
                supported.update(str(value) for value in list(metadata.get("supported_requirement_ids") or []) if str(value))
    return supported


def trim_structured_cv_for_page_fit(
    structured_cv: dict[str, Any],
    provenance: list[dict[str, Any]] | None = None,
    *,
    content_plan: dict[str, Any] | None = None,
) -> dict[str, Any] | tuple[dict[str, Any], list[str]]:
    if content_plan is not None:
        trimmed = deepcopy(structured_cv)
        sections = trimmed.get("sections")
        if not isinstance(sections, dict):
            return trimmed, []
        approved_claims = [item for item in list(content_plan.get("approved_claims") or []) if isinstance(item, dict)]
        protected_ids = {
            str(item.get("claim_id") or item.get("evidence_id") or "").strip().casefold()
            for item in approved_claims
            if str(item.get("claim_id") or item.get("evidence_id") or "").strip()
            and list(item.get("supports_requirements") or [])
        }
        baseline = content_plan.get("baseline_profile_records") or content_plan.get("records_selected_for_render") or {}
        baseline_record_ids: set[str] = set()
        section_source_keys = {
            "experience": "experiences",
            "projects": "projects",
            "certifications": "certifications",
        }
        for section_key, source_key in section_source_keys.items():
            for record in list(baseline.get(source_key) or []) if isinstance(baseline, dict) else []:
                if not isinstance(record, dict):
                    continue
                for key in ("canonical_record_id", "record_id", "id"):
                    value = str(record.get(key) or "").strip().casefold()
                    if value:
                        baseline_record_ids.add(f"{section_key}:{value}")
        baseline_aliases: set[str] = set()
        baseline_keys = {
            "experience": "experiences",
            "projects": "projects",
            "certifications": "certifications",
        }
        for section_key, source_key in baseline_keys.items():
            for record in list(baseline.get(source_key) or []) if isinstance(baseline, dict) else []:
                if not isinstance(record, dict):
                    continue
                for key in ("canonical_record_id", "record_id", "id", "evidence_id", "name", "title"):
                    value = str(record.get(key) or "").strip().casefold()
                    if value:
                        baseline_aliases.add(value)
                if section_key == "experience":
                    role_company = " ".join(
                        str(record.get(key) or "").strip().casefold()
                        for key in ("role", "company")
                        if str(record.get(key) or "").strip()
                    )
                    if role_company:
                        baseline_aliases.add(role_company)
        before_record_ids = {
            f"{section_key}:{str(item.get(key) or '').strip().casefold()}"
            for section_key in section_source_keys
            for item in list(sections.get(section_key) or [])
            if isinstance(item, dict)
            for key in ("canonical_record_id", "record_id", "id")
            if f"{section_key}:{str(item.get(key) or '').strip().casefold()}" in baseline_record_ids
        }
        changes: list[str] = []
        for section_key in ("publications", "certifications", "languages", "projects"):
            items = list(sections.get(section_key) or [])
            candidates = [
                (index, item)
                for index, item in enumerate(items)
                if _trim_item_identity(item) not in protected_ids
                and _trim_item_identity(item) not in baseline_aliases
                and not (
                    isinstance(item, dict)
                    and " ".join(
                        str(item.get(key) or "").strip().casefold()
                        for key in ("role", "company")
                        if str(item.get(key) or "").strip()
                    ) in baseline_aliases
                )
                and not (isinstance(item, dict) and bool(item.get("required")))
            ]
            if not candidates:
                continue
            index, item = min(candidates, key=lambda pair: (_trim_item_identity(pair[1]), pair[0]))
            items.pop(index)
            sections[section_key] = items
            changes.append(f"removed_{section_key}:{_trim_item_identity(item)}")
        after_record_ids = {
            f"{section_key}:{str(item.get(key) or '').strip().casefold()}"
            for section_key in section_source_keys
            for item in list(sections.get(section_key) or [])
            if isinstance(item, dict)
            for key in ("canonical_record_id", "record_id", "id")
            if f"{section_key}:{str(item.get(key) or '').strip().casefold()}" in baseline_record_ids
        }
        if before_record_ids != after_record_ids:
            raise ValueError("page-fit trim removed a canonical profile record")
        return trimmed, changes
    """Remove only unprotected, optional content in deterministic order."""
    trimmed = deepcopy(structured_cv)
    by_key = _provenance_by_key(provenance)
    sections = trimmed.get("sections")
    if not isinstance(sections, dict) or not by_key:
        return trimmed
    candidates: list[tuple[str, int, int]] = []
    for section in ("experience", "projects", "education", "certifications", "publications", "languages"):
        items = sections.get(section)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            metadata = _render_item_provenance_for(by_key, section, item)
            if metadata is None or bool(metadata.get("protected", True)):
                continue
            candidates.append((section, index, len(list(item.get("bullets") or []))))
    for section, index, bullet_count in sorted(candidates, key=lambda value: (-value[2], value[0], -value[1])):
        items = sections.get(section)
        if not isinstance(items, list) or index >= len(items):
            continue
        item = items[index]
        if bullet_count > 1:
            item["bullets"] = list(item.get("bullets") or [])[:-1]
            return trimmed
        del items[index]
        return trimmed
    return trimmed


def _execute_cv_generation_runtime(
    jd: dict[str, Any],
    evidence: list[dict[str, Any]],
    gap: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
    *,
    fit_classification: str,
    evidence_selection_summary: dict[str, Any] | None = None,
    repair_missing_sections: list[str] | None = None,
    content_plan: dict[str, Any] | None = None,
    target_sections: list[str] | None = None,
    authorized_profile: dict[str, Any] | None = None,
    max_output_tokens: int | None = None,
    ranking_cv_handoff: dict[str, Any] | None = None,
    adapter: LlmAdapter | None = None,
    validator: Any | None = None,
) -> LlmRuntimeResult:
    generation_profile = authorized_profile if authorized_profile is not None else profile
    generation_gap = (
        _project_authorized_gap(gap, evidence)
        if authorized_profile is not None
        else gap
    )
    provider_profile = {
        key: value
        for key, value in generation_profile.items()
        if key not in {"candidate_profile_id", "revision"}
    }
    template_path = _resolve_template_path(config)
    template_str = Path(template_path).read_text(encoding="utf-8")
    prompt = build_structured_generation_prompt(
        jd=jd,
        evidence=evidence,
        gap=generation_gap,
        template=template_str,
        profile=provider_profile,
        config=config,
        evidence_selection_summary=evidence_selection_summary,
        repair_missing_sections=repair_missing_sections,
        content_plan=content_plan,
        target_sections=target_sections,
    )
    request = LlmTaskRequest(
        routing_part="cv_generation_structured_write",
        prompt=prompt,
        response_mode="json_schema",
        instructions=(
            "Generate one FitCV structured CV document. Follow the prompt exactly, "
            "obey the rendering reference template, and return only JSON matching the schema."
        ),
        schema_name="fitcv_structured_cv_document",
        schema=build_live_structured_cv_response_schema(config=config),
        schema_strict=False,
        max_output_tokens=max_output_tokens,
    )

    def _parser(response: LlmAdapterResponse) -> dict[str, Any]:
        response_payload = _extract_json_payload(response.raw_text)
        structured_cv = _normalize_structured_cv(
            response_payload,
            jd=jd,
            evidence=evidence,
            profile=provider_profile,
            config=config,
            fit_classification=fit_classification,
            ranking_cv_handoff=ranking_cv_handoff,
            content_plan=content_plan,
        )
        return {
            "structured_cv": structured_cv,
            "markdown": render_cv_markdown(structured_cv, config),
        }

    def _structural_validator(value: dict[str, Any]) -> LlmValidationResult:
        structured_cv = value.get("structured_cv")
        if not isinstance(structured_cv, dict):
            return LlmValidationResult(valid=False, errors=["structured_cv missing"], details={})
        validate_structured_cv(structured_cv, config=config)
        return LlmValidationResult(valid=True, errors=[], details={})

    return execute_llm_task(
        request,
        parser=_parser,
        validator=validator or _structural_validator,
        adapter=adapter,
        resolved_route=resolve_llm_routing(
            "cv_generation_structured_write", runtime_config=config
        ),
    )


def _runtime_value_or_raise(result: LlmRuntimeResult) -> dict[str, Any]:
    if result.status == "succeeded" and isinstance(result.parsed_value, dict):
        value = dict(result.parsed_value)
        value["llm_runtime_evidence"] = project_llm_runtime_evidence(result)
        return value
    message = result.failure.message if result.failure else "LLM runtime failed."
    error = RuntimeError(message)
    setattr(error, "llm_runtime_evidence", project_llm_runtime_evidence(result))
    raise error


def generate_structured_cv(
    jd: dict[str, Any],
    evidence: list[dict[str, Any]],
    gap: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
    *,
    fit_classification: str,
    evidence_selection_summary: dict[str, Any] | None = None,
    repair_missing_sections: list[str] | None = None,
    content_plan: dict[str, Any] | None = None,
    target_sections: list[str] | None = None,
    authorized_profile: dict[str, Any] | None = None,
    max_output_tokens: int | None = None,
    ranking_cv_handoff: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call the LLM to generate a structured CV document."""
    value = _runtime_value_or_raise(
        _execute_cv_generation_runtime(
            jd,
            evidence,
            gap,
            profile,
            config,
            fit_classification=fit_classification,
            evidence_selection_summary=evidence_selection_summary,
            repair_missing_sections=repair_missing_sections,
            content_plan=content_plan,
            target_sections=target_sections,
            authorized_profile=authorized_profile,
            max_output_tokens=max_output_tokens,
            ranking_cv_handoff=ranking_cv_handoff,
        )
    )
    return dict(value["structured_cv"])


def generate_cv(
    jd: dict[str, Any],
    evidence: list[dict[str, Any]],
    gap: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
    *,
    fit_classification: str = "unclassified",
    evidence_selection_summary: dict[str, Any] | None = None,
    repair_missing_sections: list[str] | None = None,
    content_plan: dict[str, Any] | None = None,
    target_sections: list[str] | None = None,
    authorized_profile: dict[str, Any] | None = None,
    max_output_tokens: int | None = None,
    ranking_cv_handoff: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate structured CV content and render markdown from it."""
    return _runtime_value_or_raise(
        _execute_cv_generation_runtime(
            jd,
            evidence,
            gap,
            profile,
            config,
            fit_classification=fit_classification,
            evidence_selection_summary=evidence_selection_summary,
            repair_missing_sections=repair_missing_sections,
            content_plan=content_plan,
            target_sections=target_sections,
            authorized_profile=authorized_profile,
            max_output_tokens=max_output_tokens,
            ranking_cv_handoff=ranking_cv_handoff,
        )
    )
