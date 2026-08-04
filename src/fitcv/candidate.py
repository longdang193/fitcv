"""@meta
name: candidate
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.candidate.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

import copy
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

_EVIDENCE_KINDS = (
    "work_achievement",
    "work_responsibility",
    "thesis",
    "seminar",
    "course",
    "academic_project",
    "project_highlight",
    "achievement",
    "certification_proof",
    "volunteer_contribution",
)

_SOURCE_REFS_FIELD = {
    "shape": "source_refs",
    "label": "Source references",
    "description": "Links this fact to exact uploaded source evidence.",
    "required": True,
}

_EVIDENCE_COLLECTION_FIELD = {
    "shape": "collection",
    "label": "Evidence",
    "description": "Atomic statements used by pipeline evidence projection.",
    "required": True,
    "item": {
        "id": {"shape": "text", "label": "ID", "required": True},
        "kind": {
            "shape": "select",
            "label": "Kind",
            "description": "Classifies this statement for explanation and display. Kind never changes relevance scoring.",
            "required": True,
            "options": [
                {"value": value, "label": value.replace("_", " ").capitalize()}
                for value in _EVIDENCE_KINDS
            ],
        },
        "title": {
            "shape": "text",
            "label": "Title",
            "description": "Optional short label for this evidence statement.",
            "required": False,
        },
        "start": {
            "shape": "month",
            "label": "Start",
            "description": "Optional start value. Use YYYY-MM or Present.",
            "required": False,
        },
        "end": {
            "shape": "month_or_present",
            "label": "End",
            "description": "Optional end value. Use YYYY-MM or Present.",
            "required": False,
        },
        "text": {
            "shape": "textarea",
            "label": "Evidence text",
            "description": "Reviewed statement projected into runtime candidate evidence.",
            "required": True,
        },
        "source_refs": _SOURCE_REFS_FIELD,
    },
}

_DERIVED_CLAIM_ITEM = {
    "id": {"shape": "text", "label": "ID", "required": True},
    "name": {"shape": "text", "label": "Name", "required": True},
    "origin": {"shape": "status", "label": "Origin", "required": True},
    "confidence": {"shape": "number", "label": "Confidence", "required": True},
    "support_status": {"shape": "status", "label": "Support status", "required": True},
    "evidence_refs": {
        "shape": "evidence_refs",
        "label": "Evidence references",
        "required": True,
    },
}

CANDIDATE_PROFILE_V2_FIELD_REGISTRY: dict[str, Any] = {
    "schema_version": "candidate-profile-fields.v1",
    "schema_revision": 1,
    "date_grammar": {
        "format": "YYYY-MM",
        "present_value": "Present",
        "optional": True,
    },
    "evidence_kinds": list(_EVIDENCE_KINDS),
    "sections": [
        {
            "id": "identity",
            "stage": "baseline",
            "shape": "object",
            "label": "Profile",
            "description": "Canonical identity and profile text.",
            "fields": {
                "name": {"shape": "text", "label": "Full name", "description": "Reviewed candidate display name.", "required": True},
                "headline": {"shape": "text", "label": "Professional headline", "description": "Optional professional headline copied from source.", "required": False},
                "summary": {"shape": "textarea", "label": "Summary", "description": "Optional profile summary based on reviewed evidence.", "required": False, "regenerable": True},
            },
        },
        {
            "id": "contact",
            "stage": "baseline",
            "shape": "object",
            "label": "Contact",
            "description": "Direct contact facts; never inferred.",
            "fields": {
                "email": {"shape": "text", "label": "Email", "description": "Optional email address copied from source.", "required": False},
                "phone": {"shape": "text", "label": "Phone", "description": "Optional phone number copied from source.", "required": False},
                "location": {"shape": "text", "label": "Location", "description": "Optional candidate location copied from source.", "required": False},
                "linkedin": {"shape": "text", "label": "LinkedIn URL", "description": "Optional LinkedIn profile URL copied from source.", "required": False},
                "github": {"shape": "text", "label": "GitHub URL", "description": "Optional GitHub profile URL copied from source.", "required": False},
                "website": {"shape": "text", "label": "Website URL", "description": "Optional personal website URL copied from source.", "required": False},
            },
        },
        {
            "id": "experiences",
            "stage": "baseline",
            "shape": "collection",
            "label": "Experience",
            "item_label": "Experience",
            "description": "One parent per company and role; each statement is separate evidence.",
            "item": {
                "id": {"shape": "text", "label": "ID", "required": True},
                "role": {"shape": "text", "label": "Role", "description": "Role title stated in source.", "required": True},
                "company": {"shape": "text", "label": "Company", "description": "Employer stated in source.", "required": True},
                "company_url": {"shape": "text", "label": "Company URL", "description": "Optional employer URL stated in source.", "required": False},
                "location": {"shape": "text", "label": "Location", "description": "Optional work location stated in source.", "required": False},
                "start": {"shape": "month", "label": "Start", "description": "Optional start value. Use YYYY-MM or Present.", "required": False},
                "end": {"shape": "month_or_present", "label": "End", "description": "Optional end value. Use YYYY-MM or Present.", "required": False},
                "source_refs": _SOURCE_REFS_FIELD,
                "evidence": _EVIDENCE_COLLECTION_FIELD,
            },
        },
        {
            "id": "education",
            "stage": "baseline",
            "shape": "collection",
            "label": "Education",
            "item_label": "Education",
            "description": "Degrees, thesis work, seminars, courses, and academic projects use same evidence shape.",
            "required_one_of": ["degree", "field"],
            "item": {
                "id": {"shape": "text", "label": "ID", "required": True},
                "institution": {"shape": "text", "label": "Institution", "description": "Institution stated in source.", "required": True},
                "degree": {"shape": "text", "label": "Degree or credential", "description": "Degree or credential stated in source; degree or field is required.", "required": False},
                "field": {"shape": "text", "label": "Field of study", "description": "Field of study stated in source; degree or field is required.", "required": False},
                "location": {"shape": "text", "label": "Location", "description": "Optional study location stated in source.", "required": False},
                "start": {"shape": "month", "label": "Start", "description": "Optional start value. Use YYYY-MM or Present.", "required": False},
                "end": {"shape": "month_or_present", "label": "End", "description": "Optional end value. Use YYYY-MM or Present.", "required": False},
                "source_refs": _SOURCE_REFS_FIELD,
                "evidence": _EVIDENCE_COLLECTION_FIELD,
            },
        },
        {
            "id": "projects",
            "stage": "baseline",
            "shape": "collection",
            "label": "Projects",
            "item_label": "Project",
            "description": "Academic, personal, and work projects use same parent and evidence shape.",
            "item": {
                "id": {"shape": "text", "label": "ID", "required": True},
                "name": {"shape": "text", "label": "Project name", "description": "Project name stated in source.", "required": True},
                "context": {"shape": "text", "label": "Context or organization", "description": "Optional project context or organization.", "required": False},
                "url": {"shape": "text", "label": "Project URL", "description": "Optional project URL.", "required": False},
                "start": {"shape": "month", "label": "Start", "description": "Optional start value. Use YYYY-MM or Present.", "required": False},
                "end": {"shape": "month_or_present", "label": "End", "description": "Optional end value. Use YYYY-MM or Present.", "required": False},
                "source_refs": _SOURCE_REFS_FIELD,
                "evidence": _EVIDENCE_COLLECTION_FIELD,
            },
        },
        *[
            {
                "id": section_id,
                "stage": "baseline",
                "shape": "collection",
                "label": label,
                "item_label": item_label,
                "description": description,
                "item": item,
            }
            for section_id, label, item_label, description, item in (
                ("achievements", "Achievements", "Achievement", "Each achievement may contain one or more traceable statements.", {"id": {"shape": "text", "label": "ID", "required": True}, "title": {"shape": "text", "label": "Title", "description": "Achievement title stated in source.", "required": True}, "issuer": {"shape": "text", "label": "Issuer", "description": "Optional issuing organization.", "required": False}, "date": {"shape": "month", "label": "Date", "description": "Optional achievement date copied from source.", "required": False}, "url": {"shape": "text", "label": "URL", "description": "Optional achievement URL.", "required": False}, "source_refs": _SOURCE_REFS_FIELD, "evidence": _EVIDENCE_COLLECTION_FIELD}),
                ("certifications", "Certifications", "Certification", "Each certification uses same evidence contract.", {"id": {"shape": "text", "label": "ID", "required": True}, "name": {"shape": "text", "label": "Certification", "description": "Certification name stated in source.", "required": True}, "issuer": {"shape": "text", "label": "Issuer", "description": "Certification issuer stated in source.", "required": True}, "date": {"shape": "month", "label": "Date", "description": "Optional issue date copied from source.", "required": False}, "expires": {"shape": "month", "label": "Expires", "description": "Optional expiry value copied from source.", "required": False}, "credential_id": {"shape": "text", "label": "Credential ID", "description": "Optional credential identifier.", "required": False}, "url": {"shape": "text", "label": "Credential URL", "description": "Optional credential URL.", "required": False}, "source_refs": _SOURCE_REFS_FIELD, "evidence": _EVIDENCE_COLLECTION_FIELD}),
                ("volunteering", "Volunteering", "Volunteer role", "Volunteer contributions compete uniformly with other evidence.", {"id": {"shape": "text", "label": "ID", "required": True}, "organization": {"shape": "text", "label": "Organization", "description": "Volunteer organization stated in source.", "required": True}, "role": {"shape": "text", "label": "Role", "description": "Volunteer role stated in source.", "required": True}, "location": {"shape": "text", "label": "Location", "description": "Optional volunteer location.", "required": False}, "start": {"shape": "month", "label": "Start", "description": "Optional start value. Use YYYY-MM or Present.", "required": False}, "end": {"shape": "month_or_present", "label": "End", "description": "Optional end value. Use YYYY-MM or Present.", "required": False}, "source_refs": _SOURCE_REFS_FIELD, "evidence": _EVIDENCE_COLLECTION_FIELD}),
                ("languages", "Languages", "Language", "Add each language and level separately.", {"id": {"shape": "text", "label": "ID", "required": True}, "name": {"shape": "text", "label": "Language", "description": "Language stated in source.", "required": True}, "level": {"shape": "text", "label": "Level", "description": "Optional proficiency level stated in source.", "required": False}, "source_refs": _SOURCE_REFS_FIELD}),
            )
        ],
        {"id": "interests", "stage": "baseline", "shape": "string_list", "label": "Interests"},
        {"id": "search_preferences", "stage": "baseline", "shape": "object", "label": "Search preferences", "fields": {}},
        *[
            {
                "id": section_id,
                "stage": "derived",
                "shape": "collection",
                "label": label,
                "item_label": item_label,
                "description": description,
                "item": _DERIVED_CLAIM_ITEM,
            }
            for section_id, label, item_label, description in (
                ("skills", "Skills", "Skill", "Each skill is independently editable and traceable."),
                ("role_families", "Role Families", "Role Family", "Each role family retains its own evidence refs."),
                ("domain_tags", "Domain Tags", "Domain Tag", "Each domain tag retains its own evidence refs."),
                ("responsibility_themes", "Responsibility Themes", "Responsibility Theme", "Each theme retains its own evidence refs."),
            )
        ],
    ],
}


def candidate_profile_field_schema() -> dict[str, Any]:
    payload = copy.deepcopy(CANDIDATE_PROFILE_V2_FIELD_REGISTRY)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["checksum"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


_V2_BASELINE_COLLECTIONS = tuple(
    section["id"]
    for section in CANDIDATE_PROFILE_V2_FIELD_REGISTRY["sections"]
    if section.get("stage") == "baseline" and section.get("shape") == "collection"
)
_V2_DERIVED_COLLECTIONS = tuple(
    section["id"]
    for section in CANDIDATE_PROFILE_V2_FIELD_REGISTRY["sections"]
    if section.get("stage") == "derived"
)
_V2_EVIDENCE_COLLECTIONS = tuple(
    section["id"]
    for section in CANDIDATE_PROFILE_V2_FIELD_REGISTRY["sections"]
    if section.get("stage") == "baseline"
    and section.get("shape") == "collection"
    and "evidence" in section.get("item", {})
)
_CANONICAL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,127}$")
_CANONICAL_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def canonical_candidate_checksum(profile: dict[str, Any]) -> str:
    canonical = json.dumps(profile, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _stable_candidate_id(prefix: str, *parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _uploaded_source_ref(document_id: str) -> dict[str, Any]:
    return {"document_id": document_id}


def _with_uploaded_source_ref(values: Any, document_id: str) -> list[dict[str, Any]]:
    refs = [copy.deepcopy(value) for value in values or [] if isinstance(value, dict)]
    if not any(ref.get("document_id") == document_id for ref in refs):
        refs.insert(0, _uploaded_source_ref(document_id))
    return refs


def _normalize_legacy_month(value: Any, *, end: bool = False) -> str:
    text = str(value or "").strip()
    if text.lower() == "present":
        return "Present"
    if re.fullmatch(r"\d{4}", text):
        return f"{text}-{'12' if end else '01'}"
    return text


def _legacy_evidence(
    *,
    parent_id: str,
    kind: str,
    text: Any,
    index: int,
    document_id: str,
    title: Any = None,
    start: Any = None,
    end: Any = None,
) -> dict[str, Any] | None:
    normalized_text = str(text or "").strip()
    if not normalized_text:
        return None
    item: dict[str, Any] = {
        "id": _stable_candidate_id(f"ev_{parent_id}", index, normalized_text),
        "kind": kind,
        "text": normalized_text,
        "source_refs": [_uploaded_source_ref(document_id)],
    }
    for key, value in (("title", title), ("start", start), ("end", end)):
        normalized = _normalize_legacy_month(value, end=key == "end") if key != "title" else str(value or "").strip()
        if normalized:
            item[key] = normalized
    return item


def _normalize_v2_parent(item: dict[str, Any], document_id: str) -> dict[str, Any]:
    normalized = copy.deepcopy(item)
    normalized["source_refs"] = _with_uploaded_source_ref(normalized.get("source_refs"), document_id)
    normalized["evidence"] = [
        {
            **copy.deepcopy(evidence),
            "source_refs": _with_uploaded_source_ref(evidence.get("source_refs"), document_id),
        }
        for evidence in normalized.get("evidence") or []
        if isinstance(evidence, dict)
    ]
    return normalized


def _adapt_legacy_parent(
    section: str,
    item: dict[str, Any],
    document_id: str,
) -> tuple[dict[str, Any], list[str]]:
    normalized = copy.deepcopy(item)
    for key in (
        "skills",
        "role_family",
        "domain_tags",
        "responsibility_themes",
        "duration",
        "tech_stack",
    ):
        normalized.pop(key, None)
    parent_id = str(normalized.get("id") or _stable_candidate_id(section[:-1], section, item))
    normalized["id"] = parent_id
    normalized["source_refs"] = [_uploaded_source_ref(document_id)]
    if section == "experiences" and "company" not in normalized and normalized.get("organization"):
        normalized["company"] = normalized.pop("organization")
    current = normalized.pop("current", None)
    end = str(normalized.get("end") or "").strip()
    if current is True and end and end.lower() != "present":
        raise ValueError("current: true contradicts end")
    if current is True:
        normalized["end"] = "Present"
    elif end.lower() == "present":
        normalized["end"] = "Present"
    evidence: list[dict[str, Any]] = []
    for index, value in enumerate(normalized.pop("evidence", []) or []):
        if not isinstance(value, dict):
            continue
        candidate = _legacy_evidence(
            parent_id=parent_id,
            kind=str(value.get("kind") or "achievement"),
            title=value.get("title"),
            text=value.get("text"),
            index=index,
            document_id=document_id,
            start=value.get("start") or value.get("date"),
            end=value.get("end"),
        )
        if candidate:
            evidence.append(candidate)
    if section == "experiences":
        for index, bullet in enumerate(normalized.pop("bullets", []) or []):
            raw = bullet.get("text") if isinstance(bullet, dict) else bullet
            candidate = _legacy_evidence(
                parent_id=parent_id,
                kind="work_achievement",
                text=raw,
                index=index,
                document_id=document_id,
            )
            if candidate:
                evidence.append(candidate)
    elif section == "education":
        thesis = normalized.pop("thesis", None)
        if isinstance(thesis, dict):
            candidate = _legacy_evidence(
                parent_id=parent_id,
                kind="thesis",
                title=thesis.get("title"),
                text=thesis.get("summary") or thesis.get("title"),
                index=len(evidence),
                document_id=document_id,
            )
            if candidate:
                evidence.append(candidate)
        for kind, key in (("course", "courses"), ("seminar", "activities")):
            for value in normalized.pop(key, []) or []:
                candidate = _legacy_evidence(
                    parent_id=parent_id,
                    kind=kind,
                    title=value,
                    text=value,
                    index=len(evidence),
                    document_id=document_id,
                )
                if candidate:
                    evidence.append(candidate)
    elif section == "projects":
        values = list(normalized.pop("highlights", []) or [])
        if normalized.get("business_value"):
            values.append(normalized.pop("business_value"))
        for value in values:
            candidate = _legacy_evidence(
                parent_id=parent_id,
                kind="project_highlight",
                text=value,
                index=len(evidence),
                document_id=document_id,
            )
            if candidate:
                evidence.append(candidate)
    elif section == "achievements":
        if not normalized.get("title") and normalized.get("text"):
            normalized["title"] = normalized["text"]
        candidate = _legacy_evidence(
            parent_id=parent_id,
            kind="achievement",
            text=normalized.pop("text", None) or normalized.get("title"),
            index=0,
            document_id=document_id,
        )
        if candidate:
            evidence.append(candidate)
    elif section == "certifications":
        if "date" not in normalized and normalized.get("year"):
            normalized["date"] = _normalize_legacy_month(normalized.pop("year"))
        if "expires" not in normalized and normalized.get("expiry"):
            normalized["expires"] = _normalize_legacy_month(normalized.pop("expiry"), end=True)
        candidate = _legacy_evidence(
            parent_id=parent_id,
            kind="certification_proof",
            title=normalized.get("name"),
            text=normalized.get("name"),
            index=0,
            document_id=document_id,
            start=normalized.get("date"),
        )
        if candidate:
            evidence.append(candidate)
    elif section == "volunteering":
        candidate = _legacy_evidence(
            parent_id=parent_id,
            kind="volunteer_contribution",
            text=normalized.pop("description", None),
            index=0,
            document_id=document_id,
        )
        if candidate:
            evidence.append(candidate)
    for field_name, end_boundary in (("start", False), ("end", True), ("date", False), ("expires", True)):
        if field_name in normalized:
            normalized[field_name] = _normalize_legacy_month(normalized[field_name], end=end_boundary)
    normalized["evidence"] = evidence
    return normalized, [entry["id"] for entry in evidence]


def adapt_candidate_profile_to_v2(
    profile: dict[str, Any],
    uploaded_source_document: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise ValueError("Candidate profile must be a mapping")
    document_id = str(uploaded_source_document["id"])
    if profile.get("schema_version") == "candidate-profile.v2":
        normalized = copy.deepcopy(profile)
        supplied_documents = []
        for document in normalized.get("source_documents") or []:
            if not isinstance(document, dict) or document.get("id") == document_id:
                continue
            supplied_documents.append({**copy.deepcopy(document), "origin": "declared"})
        normalized["source_documents"] = [copy.deepcopy(uploaded_source_document), *supplied_documents]
        normalized.setdefault("contact", {})
        normalized.setdefault("headline", None)
        normalized.setdefault("summary", None)
        normalized.setdefault("interests", [])
        if "search_preferences" not in normalized and "preferences" in normalized:
            normalized["search_preferences"] = normalized.pop("preferences")
        for section in _V2_BASELINE_COLLECTIONS:
            values = normalized.get(section) or []
            if section in _V2_EVIDENCE_COLLECTIONS:
                normalized[section] = [
                    _normalize_v2_parent(value, document_id)
                    for value in values
                    if isinstance(value, dict)
                ]
            else:
                normalized[section] = [
                    {
                        **copy.deepcopy(value),
                        "source_refs": _with_uploaded_source_ref(value.get("source_refs"), document_id),
                    }
                    for value in values
                    if isinstance(value, dict)
                ]
        for section in _V2_DERIVED_COLLECTIONS:
            claims: list[dict[str, Any]] = []
            for value in normalized.get(section) or []:
                if not isinstance(value, dict):
                    value = {"name": value}
                claim = copy.deepcopy(value)
                claim.setdefault("origin", "user")
                claim.setdefault("confidence", 1.0)
                claim.setdefault("support_status", "supported")
                claim["evidence_refs"] = list(dict.fromkeys(claim.get("evidence_refs") or []))
                claims.append(claim)
            normalized[section] = claims
        normalized.setdefault("search_preferences", {})
        normalized.pop("preferences", None)
        return normalized

    normalized: dict[str, Any] = {
        "schema_version": "candidate-profile.v2",
        "source_documents": [copy.deepcopy(uploaded_source_document)],
        "name": str(profile.get("name") or "Candidate").strip(),
        "headline": profile.get("headline"),
        "summary": profile.get("summary"),
        "contact": copy.deepcopy(profile.get("contact") or {}),
        "interests": list(profile.get("interests") or []),
        "search_preferences": copy.deepcopy(profile.get("search_preferences") or profile.get("preferences") or {}),
    }
    parent_evidence: dict[str, list[str]] = {}
    legacy_claim_refs: dict[str, dict[str, set[str]]] = {
        "skills": {},
        "role_families": {},
        "domain_tags": {},
        "responsibility_themes": {},
    }
    for section in _V2_BASELINE_COLLECTIONS:
        if section == "languages":
            normalized[section] = [
                {
                    **copy.deepcopy(value),
                    "source_refs": [_uploaded_source_ref(document_id)],
                }
                for value in profile.get(section) or []
                if isinstance(value, dict)
            ]
            continue
        adapted: list[dict[str, Any]] = []
        for value in profile.get(section) or []:
            if not isinstance(value, dict):
                continue
            metadata = {
                "skills": [
                    *list(value.get("skills") or []),
                    *[
                        skill
                        for bullet in value.get("bullets") or []
                        if isinstance(bullet, dict)
                        for skill in bullet.get("skills") or []
                    ],
                ],
                "role_families": [value.get("role_family")],
                "domain_tags": list(value.get("domain_tags") or []),
                "responsibility_themes": list(value.get("responsibility_themes") or []),
            }
            parent, evidence_ids = _adapt_legacy_parent(section, value, document_id)
            adapted.append(parent)
            parent_evidence[parent["id"]] = evidence_ids
            for claim_section, names in metadata.items():
                for name in names:
                    normalized_name = str(name or "").strip()
                    if normalized_name:
                        legacy_claim_refs[claim_section].setdefault(normalized_name, set()).update(evidence_ids)
        normalized[section] = adapted
    skills: list[dict[str, Any]] = []
    for index, value in enumerate(profile.get("skills") or []):
        claim = copy.deepcopy(value) if isinstance(value, dict) else {"name": value}
        refs: list[str] = []
        for ref in claim.get("evidence_refs") or []:
            refs.extend(parent_evidence.get(ref, [ref]))
        claim.update(
            {
                "id": claim.get("id") or _stable_candidate_id("skill", index, claim.get("name")),
                "origin": claim.get("origin") or "user",
                "confidence": claim.get("confidence", 1.0),
                "support_status": claim.get("support_status") or "supported",
                "evidence_refs": list(dict.fromkeys(refs)),
            }
        )
        skills.append(claim)
    existing_skills = {str(claim.get("name") or "").casefold(): claim for claim in skills}
    for name, refs in legacy_claim_refs["skills"].items():
        existing = existing_skills.get(name.casefold())
        if existing is not None:
            existing["evidence_refs"] = list(dict.fromkeys([*existing["evidence_refs"], *sorted(refs)]))
            continue
        skills.append(
            {
                "id": _stable_candidate_id("skill", len(skills), name),
                "name": name,
                "origin": "extracted_explicit",
                "confidence": 1.0,
                "support_status": "supported" if refs else "unsupported",
                "evidence_refs": sorted(refs),
            }
        )
    normalized["skills"] = skills
    for section in ("role_families", "domain_tags", "responsibility_themes"):
        normalized[section] = [
            {
                "id": _stable_candidate_id(section[:-1], index, name),
                "name": name,
                "origin": "extracted_explicit",
                "confidence": 1.0,
                "support_status": "supported" if refs else "unsupported",
                "evidence_refs": sorted(refs),
            }
            for index, (name, refs) in enumerate(legacy_claim_refs[section].items())
        ]
    return normalized

def converge_candidate_profile_for_runtime(profile: dict[str, Any]) -> dict[str, Any]:
    """Return one validated v2-compatible runtime snapshot without mutating input."""
    if profile.get("schema_version") == "candidate-profile.v2":
        normalized = copy.deepcopy(profile)
    else:
        checksum = canonical_candidate_checksum(profile)
        normalized = adapt_candidate_profile_to_v2(
            profile,
            {
                "id": f"doc_runtime_{checksum[:16]}",
                "origin": "uploaded",
                "filename": "candidate-profile.v1.json",
                "media_type": "application/json",
                "sha256": checksum,
                "parser": {"name": "fitcv-v1-runtime-adapter", "version": "1"},
            },
        )
    errors = validate_candidate_profile_v2(normalized)
    if errors:
        raise ValueError("; ".join(errors))
    return normalized


def validate_candidate_profile_v2(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(profile, dict) or profile.get("schema_version") != "candidate-profile.v2":
        return ["schema_version must be candidate-profile.v2"]
    if not str(profile.get("name") or "").strip():
        errors.append("name is required")
    section_registry = {
        section["id"]: section
        for section in CANDIDATE_PROFILE_V2_FIELD_REGISTRY["sections"]
    }
    allowed_top_level = {
        "schema_version",
        "source_documents",
        *section_registry["identity"]["fields"],
        "contact",
        *(section_id for section_id in section_registry if section_id not in {"identity", "contact"}),
    }
    for key in sorted(set(profile) - allowed_top_level):
        errors.append(f"unsupported top-level field: {key}")
    contact = profile.get("contact") or {}
    if not isinstance(contact, dict):
        errors.append("contact must be a mapping")
    else:
        allowed_contact = set(section_registry["contact"]["fields"])
        for key in sorted(set(contact) - allowed_contact):
            errors.append(f"unsupported contact field: {key}")
    documents = [value for value in profile.get("source_documents") or [] if isinstance(value, dict)]
    document_ids = [str(value.get("id") or "") for value in documents]
    if len(document_ids) != len(set(document_ids)) or any(not value for value in document_ids):
        errors.append("source document IDs must be non-empty and unique")
    uploaded_ids = {str(value.get("id")) for value in documents if value.get("origin") == "uploaded"}
    if not uploaded_ids:
        errors.append("at least one uploaded source document is required")
    all_ids: set[str] = set()
    evidence_ids: set[str] = set()

    def register_id(value: Any, label: str) -> None:
        identifier = str(value or "")
        if not _CANONICAL_ID_PATTERN.fullmatch(identifier):
            errors.append(f"invalid {label} ID: {identifier!r}")
        elif identifier in all_ids:
            errors.append(f"duplicate ID: {identifier}")
        else:
            all_ids.add(identifier)

    def validate_date(value: Any, label: str) -> None:
        text = str(value or "").strip()
        if text and text != "Present" and not _CANONICAL_MONTH_PATTERN.fullmatch(text):
            errors.append(f"invalid {label}: {text!r}")

    def validate_refs(values: Any, label: str, *, require_uploaded: bool) -> None:
        refs = [value for value in values or [] if isinstance(value, dict)]
        if len(refs) != len(values or []):
            errors.append(f"invalid source_refs in {label}")
        serialized = [json.dumps(value, sort_keys=True, separators=(",", ":")) for value in refs]
        if len(serialized) != len(set(serialized)):
            errors.append(f"duplicate source_refs in {label}")
        resolved = {str(value.get("document_id") or "") for value in refs}
        dangling = sorted(resolved - set(document_ids))
        if dangling:
            errors.append(f"dangling source_refs in {label}: {dangling}")
        if require_uploaded and not (resolved & uploaded_ids):
            errors.append(f"{label} requires uploaded source_refs")
        for ref in refs:
            locator = ref.get("locator")
            if locator is None:
                continue
            if not isinstance(locator, dict):
                errors.append(f"invalid locator in {label}")
                continue
            kind = locator.get("kind")
            if kind == "markdown_lines":
                start = locator.get("start")
                end = locator.get("end")
                if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
                    errors.append(f"invalid markdown locator in {label}")
            elif kind == "docx_paragraph":
                if locator.get("part") not in {"document", "header", "footer"} or not isinstance(locator.get("paragraph"), int) or locator["paragraph"] < 1:
                    errors.append(f"invalid DOCX paragraph locator in {label}")
            elif kind == "docx_table_cell":
                coordinates = (locator.get("table"), locator.get("row"), locator.get("cell"))
                if locator.get("part") not in {"document", "header", "footer"} or any(not isinstance(value, int) or value < 1 for value in coordinates):
                    errors.append(f"invalid DOCX table locator in {label}")
            else:
                errors.append(f"invalid locator kind in {label}: {kind!r}")

    for document in documents:
        register_id(document.get("id"), "source document")
        if document.get("origin") not in {"uploaded", "declared"}:
            errors.append(f"invalid source document origin: {document.get('origin')!r}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(document.get("sha256") or "")):
            errors.append(f"invalid source document sha256: {document.get('id')!r}")

    for section in _V2_BASELINE_COLLECTIONS:
        values = profile.get(section)
        if not isinstance(values, list):
            errors.append(f"{section} must be a list")
            continue
        for item in values:
            if not isinstance(item, dict):
                errors.append(f"{section} entries must be mappings")
                continue
            register_id(item.get("id"), section)
            section_definition = section_registry[section]
            allowed_fields = set(section_definition.get("item", {}))
            for key in sorted(set(item) - allowed_fields):
                errors.append(f"unsupported field in {section}/{item.get('id')}: {key}")
            for field_name, field_definition in section_definition.get("item", {}).items():
                if field_definition.get("required") and field_name not in {"source_refs", "evidence"} and not str(item.get(field_name) or "").strip():
                    errors.append(f"{section}/{item.get('id')} requires {field_name}")
            required_one_of = section_definition.get("required_one_of") or []
            if required_one_of and not any(str(item.get(field) or "").strip() for field in required_one_of):
                errors.append(f"{section}/{item.get('id')} requires one of {required_one_of}")
            validate_refs(item.get("source_refs"), f"{section}/{item.get('id')}", require_uploaded=True)
            for field_name, field_definition in section_definition.get("item", {}).items():
                if field_definition.get("shape") in {"month", "month_or_present"}:
                    validate_date(item.get(field_name), f"{section}.{field_name}")
            if "current" in item:
                errors.append(f"{section}/{item.get('id')} cannot contain current")
            for evidence in item.get("evidence") or []:
                if not isinstance(evidence, dict):
                    errors.append(f"{section} evidence entries must be mappings")
                    continue
                register_id(evidence.get("id"), "evidence")
                evidence_id = str(evidence.get("id") or "")
                evidence_ids.add(evidence_id)
                allowed_evidence_fields = set(_EVIDENCE_COLLECTION_FIELD["item"])
                for key in sorted(set(evidence) - allowed_evidence_fields):
                    errors.append(f"unsupported field in evidence/{evidence_id}: {key}")
                if evidence.get("kind") not in _EVIDENCE_KINDS:
                    errors.append(f"invalid evidence kind: {evidence.get('kind')!r}")
                if not str(evidence.get("text") or "").strip():
                    errors.append(f"evidence {evidence_id} requires text")
                validate_date(evidence.get("start"), "evidence.start")
                validate_date(evidence.get("end"), "evidence.end")
                validate_refs(evidence.get("source_refs"), f"evidence/{evidence_id}", require_uploaded=True)
    for section in _V2_DERIVED_COLLECTIONS:
        values = profile.get(section)
        if not isinstance(values, list):
            errors.append(f"{section} must be a list")
            continue
        for claim in values:
            if not isinstance(claim, dict):
                errors.append(f"{section} entries must be mappings")
                continue
            register_id(claim.get("id"), section)
            for key in sorted(set(claim) - set(_DERIVED_CLAIM_ITEM)):
                errors.append(f"unsupported field in {section}/{claim.get('id')}: {key}")
            if not str(claim.get("name") or "").strip():
                errors.append(f"{section}/{claim.get('id')} requires name")
            confidence = claim.get("confidence")
            if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
                errors.append(f"{section}/{claim.get('id')} has invalid confidence")
    for section in _V2_DERIVED_COLLECTIONS:
        for claim in profile.get(section) or []:
            if not isinstance(claim, dict):
                continue
            dangling = sorted(set(claim.get("evidence_refs") or []) - evidence_ids)
            if dangling:
                errors.append(f"dangling evidence_refs in {section}/{claim.get('id')}: {dangling}")
    return errors



# ── required profile sections ─────────────────────────────────────────────────

_REQUIRED_SECTIONS = ["experiences", "skills", "projects", "achievements", "preferences"]
_ID_BEARING_SECTIONS = ("experiences", "projects", "achievements", "certifications", "education")
_EVIDENCE_REF_SECTIONS = ("skills", "achievements")
_ROLE_INFERENCE_LIMIT = 4
_MAX_INFERRED_ROLE_FAMILIES = 2
_MAX_INFERRED_DOMAINS = 3
_ROLE_NOISE_TOKENS = frozenset(
    {
        "jr",
        "junior",
        "sr",
        "senior",
        "lead",
        "staff",
        "principal",
        "freelance",
        "contract",
    }
)
_UPPERCASE_ROLE_PARTS = frozenset({"ai", "bi", "dbt", "etl", "llm", "ml", "mlops", "nlp", "sql"})
_FALLBACK_ROLE_FAMILY_BY_ROLE = {
    "analytics engineer": "data_engineering",
    "bi analyst": "analytics",
    "business intelligence analyst": "analytics",
    "data analyst": "analytics",
    "data engineer": "data_engineering",
    "data scientist": "data_science",
    "machine learning engineer": "ml_engineering",
    "ml engineer": "ml_engineering",
}

_PREFERENCE_TEXT_KEYS = ("target_role", "seniority_target", "salary_range", "notice_period")
_PREFERENCE_LIST_KEYS = (
    "location_types",
    "locations",
    "domains",
    "role_families",
    "exclude_contract_types",
    "exclude_experience_levels",
)
_EXPERIENCE_LIST_KEYS = ("domain_tags", "responsibility_themes")
_PROJECT_LIST_KEYS = ("domain_tags", "responsibility_themes")
_ACHIEVEMENT_LIST_KEYS = ("domain_tags",)


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text


def _normalize_text_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    seen_values: set[str] = set()
    for value in values:
        text = _normalize_optional_text(value)
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen_values:
            continue
        seen_values.add(lowered)
        normalized.append(lowered)
    return normalized


def _normalize_profile_alignment_metadata(profile: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(profile)

    preferences = dict(normalized.get("preferences") or {})
    for key in _PREFERENCE_TEXT_KEYS:
        text = _normalize_optional_text(preferences.get(key))
        if text is not None:
            preferences[key] = text
    for key in _PREFERENCE_LIST_KEYS:
        if key in preferences:
            preferences[key] = _normalize_text_list(preferences.get(key))
    normalized["preferences"] = preferences

    experiences: list[dict[str, Any]] = []
    for experience in normalized.get("experiences") or []:
        if not isinstance(experience, dict):
            experiences.append(experience)
            continue
        normalized_experience = dict(experience)
        role_family = _normalize_optional_text(normalized_experience.get("role_family"))
        if role_family is not None:
            normalized_experience["role_family"] = role_family.lower()
        for key in _EXPERIENCE_LIST_KEYS:
            if key in normalized_experience:
                normalized_experience[key] = _normalize_text_list(normalized_experience.get(key))
        experiences.append(normalized_experience)
    normalized["experiences"] = experiences

    projects: list[dict[str, Any]] = []
    for project in normalized.get("projects") or []:
        if not isinstance(project, dict):
            projects.append(project)
            continue
        normalized_project = dict(project)
        for key in _PROJECT_LIST_KEYS:
            if key in normalized_project:
                normalized_project[key] = _normalize_text_list(normalized_project.get(key))
        projects.append(normalized_project)
    normalized["projects"] = projects

    achievements: list[dict[str, Any]] = []
    for achievement in normalized.get("achievements") or []:
        if not isinstance(achievement, dict):
            achievements.append(achievement)
            continue
        normalized_achievement = dict(achievement)
        for key in _ACHIEVEMENT_LIST_KEYS:
            if key in normalized_achievement:
                normalized_achievement[key] = _normalize_text_list(normalized_achievement.get(key))
        achievements.append(normalized_achievement)
    normalized["achievements"] = achievements

    normalized["skills"] = _normalize_skill_entries(normalized.get("skills"))

    return normalized


def _normalize_skill_entries(values: Any) -> list[Any]:
    if not isinstance(values, list):
        return []
    normalized: list[Any] = []
    for value in values:
        if isinstance(value, dict):
            normalized.append(value)
            continue
        if isinstance(value, str):
            skill_name = value.strip()
            if skill_name:
                normalized.append({"name": skill_name})
            continue
        normalized.append(value)
    return normalized


def _ensure_normalized_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Return profile with additive alignment metadata normalized."""
    return _normalize_profile_alignment_metadata(profile)


# ── loading ───────────────────────────────────────────────────────────────────

def load_profile_yaml(path: str | Path) -> dict[str, Any]:
    """Load and return the candidate profile from a YAML file.

    Raises:
        FileNotFoundError: if the file does not exist.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Candidate profile not found: {file_path}")
    with open(file_path, encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    return _validate_profile_payload(loaded, "YAML")


def load_profile_json_text(payload: str) -> dict[str, Any]:
    """Parse and validate a candidate profile from raw JSON text.

    Raises:
        ValueError: if payload is not valid JSON, not a top-level object,
                    or fails existing `validate_profile()` validation.
    """
    profile = _parse_json_profile_payload(payload)
    return _validate_profile_payload(profile, "JSON")


def _parse_json_profile_payload(payload: str) -> Any:
    import json
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in candidate profile: {exc}") from exc

def _validate_profile_payload(profile: Any, source_format: str) -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise ValueError(
            f"Candidate profile must be a {source_format} object, got {type(profile).__name__}"
        )
    errors = validate_profile(profile)
    if errors:
        raise ValueError(f"Candidate profile validation failed: {'; '.join(errors)}")
    normalized_profile = _ensure_normalized_profile(profile)
    return normalized_profile  # type: ignore[return-value]

def load_profile_text(payload: str, *, format_hint: str = "auto") -> dict[str, Any]:
    """Parse and validate a candidate profile from JSON or YAML text.

    `format_hint` may be "json", "yaml", or "auto" (default).
    """
    hint = str(format_hint or "auto").strip().lower()
    if hint not in {"json", "yaml", "auto"}:
        raise ValueError(f"Unsupported candidate profile format_hint: {format_hint!r}")

    if hint in {"json", "auto"}:
        try:
            return _validate_profile_payload(_parse_json_profile_payload(payload), "JSON")
        except ValueError:
            if hint == "json":
                raise

    if hint in {"yaml", "auto"}:
        try:
            parsed_yaml = yaml.safe_load(payload)
        except yaml.YAMLError as exc:
            raise ValueError("Invalid YAML in candidate profile") from exc
        return _validate_profile_payload(parsed_yaml, "YAML")

    raise ValueError("Candidate profile must be valid JSON or YAML")
def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9_]+", " ", value.lower())).strip()


def _display_role_title(value: str) -> str:
    parts = []
    for part in value.split():
        if part in _UPPERCASE_ROLE_PARTS:
            parts.append(part.upper())
        else:
            parts.append(part.capitalize())
    return " ".join(parts)


def _role_taxonomy(config: dict[str, Any] | None) -> dict[str, Any]:
    raw_taxonomy = (config or {}).get("role_taxonomy")
    if not isinstance(raw_taxonomy, dict):
        return {}
    return raw_taxonomy


def _canonical_role_map(config: dict[str, Any] | None) -> dict[str, str]:
    raw_map = _role_taxonomy(config).get("canonical_role_by_alias")
    if not isinstance(raw_map, dict):
        return {}
    return {
        _normalize_text(str(alias)): _normalize_text(str(canonical))
        for alias, canonical in raw_map.items()
        if _normalize_text(str(alias)) and _normalize_text(str(canonical))
    }


def _role_family_map(config: dict[str, Any] | None) -> dict[str, str]:
    raw_map = _role_taxonomy(config).get("role_family_by_role")
    if not isinstance(raw_map, dict):
        return {}
    return {
        _normalize_text(str(role)): _normalize_text(str(family))
        for role, family in raw_map.items()
        if _normalize_text(str(role)) and _normalize_text(str(family))
    }


def _strip_role_noise(normalized_role: str) -> str:
    filtered_tokens = [token for token in normalized_role.split() if token not in _ROLE_NOISE_TOKENS]
    return " ".join(filtered_tokens).strip()


def _first_matching_role_alias(role_text: str, alias_map: dict[str, str]) -> str | None:
    for candidate in (role_text, _strip_role_noise(role_text)):
        if not candidate:
            continue
        direct_match = alias_map.get(candidate)
        if direct_match:
            return direct_match
        for alias in sorted(alias_map.keys(), key=len, reverse=True):
            if alias and alias in candidate:
                return alias_map[alias]
    return None


def canonicalize_role_title(role_text: str | None, config: dict[str, Any] | None = None) -> str | None:
    normalized_role = _normalize_text(role_text)
    if not normalized_role:
        return None
    alias_map = _canonical_role_map(config)
    if not alias_map:
        return None
    return _first_matching_role_alias(normalized_role, alias_map)


def infer_role_family(
    role_text: str | None,
    *,
    explicit_family: str | None = None,
    config: dict[str, Any] | None = None,
) -> str | None:
    normalized_explicit = _normalize_text(explicit_family)
    if normalized_explicit:
        return normalized_explicit

    role_family_by_role = _role_family_map(config)
    normalized_role = _normalize_text(role_text)
    if not normalized_role:
        return None

    if role_family_by_role:
        canonical_role = canonicalize_role_title(role_text, config)
        if canonical_role:
            configured_family = role_family_by_role.get(canonical_role)
            if configured_family:
                return configured_family
        direct_family = role_family_by_role.get(normalized_role)
        if direct_family:
            return direct_family

    return _first_matching_role_alias(normalized_role, _FALLBACK_ROLE_FAMILY_BY_ROLE)


def _is_missing_preference(value: Any) -> bool:
    return value in (None, "", [])


def _rank_weighted_labels(
    weighted_labels: list[tuple[str, int, int]],
    *,
    limit: int,
) -> list[str]:
    totals: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    for label, weight, seen_index in weighted_labels:
        if not label:
            continue
        totals[label] = totals.get(label, 0) + weight
        first_seen.setdefault(label, seen_index)
    ordered = sorted(
        totals,
        key=lambda label: (-totals[label], first_seen[label], label),
    )
    return ordered[:limit]


def _infer_target_role(profile: dict[str, Any], config: dict[str, Any] | None) -> str | None:
    experiences = list(profile.get("experiences") or [])[:_ROLE_INFERENCE_LIMIT]
    weighted_roles: list[tuple[str, int, int]] = []
    total_experiences = len(experiences)
    for index, experience in enumerate(experiences):
        canonical_role = canonicalize_role_title(str(experience.get("role") or ""), config)
        if not canonical_role:
            continue
        weighted_roles.append((canonical_role, total_experiences - index, index))
    ranked_roles = _rank_weighted_labels(weighted_roles, limit=1)
    if not ranked_roles:
        return None
    return _display_role_title(ranked_roles[0])


def _infer_role_families(profile: dict[str, Any], config: dict[str, Any] | None) -> list[str]:
    experiences = list(profile.get("experiences") or [])[:_ROLE_INFERENCE_LIMIT]
    weighted_families: list[tuple[str, int, int]] = []
    total_experiences = len(experiences)
    for index, experience in enumerate(experiences):
        family = infer_role_family(
            str(experience.get("role") or ""),
            explicit_family=str(experience.get("role_family") or "") or None,
            config=config,
        )
        if not family:
            continue
        weighted_families.append((family, total_experiences - index, index))
    return _rank_weighted_labels(weighted_families, limit=_MAX_INFERRED_ROLE_FAMILIES)


def _infer_domains(profile: dict[str, Any]) -> list[str]:
    weighted_domains: list[tuple[str, int, int]] = []
    experiences = list(profile.get("experiences") or [])
    total_experiences = len(experiences)
    for index, experience in enumerate(experiences):
        weight = total_experiences - index
        for domain in experience.get("domain_tags") or []:
            normalized_domain = _normalize_text(str(domain))
            if normalized_domain:
                weighted_domains.append((normalized_domain, weight, index))

    projects = list(profile.get("projects") or [])
    project_offset = len(weighted_domains) + len(experiences)
    for index, project in enumerate(projects):
        for domain in project.get("domain_tags") or []:
            normalized_domain = _normalize_text(str(domain))
            if normalized_domain:
                weighted_domains.append((normalized_domain, 1, project_offset + index))

    return _rank_weighted_labels(weighted_domains, limit=_MAX_INFERRED_DOMAINS)


def infer_effective_preferences(
    profile: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = _ensure_normalized_profile(profile)
    preferences = dict(profile.get("preferences") or {})
    inferred_preferences: dict[str, Any] = {}
    preference_sources: dict[str, str] = {}

    if _is_missing_preference(preferences.get("target_role")):
        inferred_target_role = _infer_target_role(profile, config)
        if inferred_target_role:
            inferred_preferences["target_role"] = inferred_target_role

    if _is_missing_preference(preferences.get("role_families")):
        inferred_role_families = _infer_role_families(profile, config)
        if inferred_role_families:
            inferred_preferences["role_families"] = inferred_role_families

    if _is_missing_preference(preferences.get("domains")):
        inferred_domains = _infer_domains(profile)
        if inferred_domains:
            inferred_preferences["domains"] = inferred_domains

    effective_preferences = dict(preferences)
    for key, inferred_value in inferred_preferences.items():
        if _is_missing_preference(preferences.get(key)):
            effective_preferences[key] = inferred_value

    for key, value in effective_preferences.items():
        if value in (None, "", []):
            continue
        preference_sources[key] = (
            "explicit_yaml"
            if not _is_missing_preference(preferences.get(key))
            else {
                "target_role": "inferred_recent_experience",
                "role_families": "inferred_role_family_map",
                "domains": "inferred_profile_domain_tags",
            }.get(key, "inferred")
        )

    return {
        "preferences": preferences,
        "inferred_preferences": inferred_preferences,
        "effective_preferences": effective_preferences,
        "preference_sources": preference_sources,
    }


# ── validation ────────────────────────────────────────────────────────────────

def validate_profile(profile: dict[str, Any]) -> list[str]:
    """Return a list of validation error strings; empty list means valid.

    Checks:
    1. Required sections are present
    2. All exp/proj/ach IDs are globally unique
    3. No dangling evidence_refs (every ref must resolve to a known ID)
    """
    errors: list[str] = []

    # ── 1. required sections ──────────────────────────────────────────────────
    for section in _REQUIRED_SECTIONS:
        if section not in profile:
            errors.append(f"Missing required section: '{section}'")

    if errors:
        return errors  # ID checks require sections; bail early

    # ── 2. ID uniqueness ──────────────────────────────────────────────────────
    all_ids: list[str] = []
    for section in _ID_BEARING_SECTIONS:
        for item in profile.get(section, []):
            if isinstance(item, dict):
                all_ids.append(str(item.get("id", "")))
    seen_ids: set[str] = set()
    for id_val in all_ids:
        if not id_val:
            errors.append("Found an experience/project/achievement without an 'id' field")
        elif id_val in seen_ids:
            errors.append(f"Duplicate ID '{id_val}' in candidate profile")
        else:
            seen_ids.add(id_val)

    # ── 3. dangling evidence_refs ─────────────────────────────────────────────
    known_ids: set[str] = set(all_ids)
    for section in _EVIDENCE_REF_SECTIONS:
        entries = profile.get(section, [])
        if section == "skills":
            entries = _normalize_skill_entries(entries)
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"Invalid {section[:-1]} entry type: {type(entry).__name__}")
                continue
            for ref in entry.get("evidence_refs", []):
                if ref not in known_ids:
                    label = entry.get("name", "?") if section == "skills" else entry.get("id", "?")
                    errors.append(
                        f"Dangling evidence_ref '{ref}' in {section[:-1]} '{label}'"
                    )

    return errors



# ── skill extraction ──────────────────────────────────────────────────────────

def flatten_skills(profile: dict[str, Any]) -> list[str]:
    """Return a deduplicated list of all skills mentioned in the profile.

    Collects from:
    - `skills[].name` (explicit skill inventory)
    - `experiences[].bullets[].skills`
    - `projects[].skills`
    """
    seen: set[str] = set()
    result: list[str] = []

    def _add(skill: str) -> None:
        if skill and skill not in seen:
            seen.add(skill)
            result.append(skill)

    # Explicit skill inventory
    for skill in profile.get("skills", []):
        if isinstance(skill, dict):
            _add(str(skill.get("name", "")))
        else:
            _add(str(skill))

    # Experience bullets
    for exp in profile.get("experiences", []):
        for bullet in exp.get("bullets", []):
            for skill in bullet.get("skills", []):
                _add(str(skill))

    # Projects
    for project in profile.get("projects", []):
        for skill in project.get("skills", []):
            _add(str(skill))

    return result


# ── BQ row preparation ────────────────────────────────────────────────────────

def prepare_profile_rows(profile: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Map a candidate profile dict to normalized row payloads.

    Returns a dict with keys: profile, experiences, projects, skills, achievements.
    Each value is a list of row dicts for downstream local processing.
    """
    profile = _ensure_normalized_profile(profile)
    now = datetime.now(tz=timezone.utc).isoformat()
    profile_id = str(uuid.uuid4())
    prefs = profile.get("preferences", {})

    # ── candidate_profile (1 row) ─────────────────────────────────────────────
    profile_rows: list[dict[str, Any]] = [{
        "profile_id":                 profile_id,
        "name":                       profile.get("name", ""),
        "headline":                   profile.get("headline", ""),
        "summary":                    profile.get("summary", ""),
        "location_types":             prefs.get("location_types", []),
        "domains":                    prefs.get("domains", []),
        "seniority_target":           prefs.get("seniority_target", ""),
        "exclude_contract_types":     prefs.get("exclude_contract_types", []),
        "exclude_experience_levels":  prefs.get("exclude_experience_levels", []),
        "updated_at":                 now,
    }]

    # ── candidate_experiences (1 row per bullet) ──────────────────────────────
    experience_rows: list[dict[str, Any]] = []
    for exp in profile.get("experiences", []):
        if not isinstance(exp, dict):
            continue
        exp_id = str(exp.get("id", ""))
        for idx, bullet in enumerate(exp.get("bullets", [])):
            if not isinstance(bullet, dict):
                continue
            experience_rows.append({
                "exp_id":           exp_id,
                "role":             exp.get("role", ""),
                "company":          exp.get("company", ""),
                "location":         exp.get("location", ""),
                "start_date":       exp.get("start", ""),
                "end_date":         exp.get("end", ""),
                "bullet_index":     idx,
                "bullet_text":      bullet.get("text", ""),
                "skills":           bullet.get("skills", []),
                "measurable_impact": bullet.get("measurable_impact", ""),
                "updated_at":       now,
            })

    # ── candidate_projects ────────────────────────────────────────────────────
    project_rows: list[dict[str, Any]] = []
    for proj in profile.get("projects", []):
        if not isinstance(proj, dict):
            continue
        project_rows.append({
            "project_id":     str(proj.get("id", "")),
            "name":           proj.get("name", ""),
            "skills":         proj.get("skills", []),
            "business_value": proj.get("business_value", ""),
            "evidence":       proj.get("evidence", ""),
            "updated_at":     now,
        })

    # ── candidate_skills ──────────────────────────────────────────────────────
    skill_rows: list[dict[str, Any]] = []
    for skill in profile.get("skills", []):
        if isinstance(skill, dict):
            skill_rows.append({
                "skill_name":    str(skill.get("name", "")),
                "level":         skill.get("level", ""),
                "years":         skill.get("years"),
                "evidence_refs": skill.get("evidence_refs", []),
                "updated_at":    now,
            })
        else:
            skill_rows.append({
                "skill_name":    str(skill or ""),
                "level":         "",
                "years":         None,
                "evidence_refs": [],
                "updated_at":    now,
            })

    # ── candidate_achievements ────────────────────────────────────────────────
    achievement_rows: list[dict[str, Any]] = []
    for ach in profile.get("achievements", []):
        if not isinstance(ach, dict):
            continue
        achievement_rows.append({
            "achievement_id": str(ach.get("id", "")),
            "text":           ach.get("text", ""),
            "category":       ach.get("category", ""),
            "evidence_refs":  ach.get("evidence_refs", []),
            "updated_at":     now,
        })

    return {
        "profile":      profile_rows,
        "experiences":  experience_rows,
        "projects":     project_rows,
        "skills":       skill_rows,
        "achievements": achievement_rows,
    }


# ── candidate profile load hook ──────────────────────────────────────────────

def load_candidate_profile(
    profile: dict[str, Any],
    config: dict[str, Any],
) -> None:
    """Normalize candidate profile load hook.

    Current SQLite product direction does not persist profile tables separately.
    """
    return
