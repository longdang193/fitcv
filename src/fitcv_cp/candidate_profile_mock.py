"""Deterministic Candidate Profile mock used for frontend approval."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

from fitcv.candidate import candidate_profile_field_schema
from fitcv_cp.app import create_app
from fitcv_cp.candidate_profile_seeds import CANDIDATE_PROFILE_SEEDS

_NOW = "2026-08-02T12:00:00+00:00"
_SOURCE_BYTES = b"# Alex Morgan\n\nProduct data analyst with SQL, Python, education, and project evidence.\n"
_SOURCE_CHECKSUM = hashlib.sha256(_SOURCE_BYTES).hexdigest()
_PROTOTYPE_BASELINE_FIELDS = (
    ("identity", "profile", ("name", "headline", "summary")),
    ("contact", "contact", ("email", "phone", "location", "linkedin", "github", "website")),
    ("experiences", "experiences", ("role", "company", "company_url", "location", "start", "end")),
    ("education", "education", ("degree", "field", "institution", "location", "start", "end")),
    ("projects", "projects", ("name", "context", "url", "start", "end")),
    ("achievements", "achievements", ("title", "issuer", "date", "url")),
    ("certifications", "certifications", ("name", "issuer", "date", "expires", "credential_id", "url")),
    ("volunteering", "volunteering", ("organization", "role", "location", "start", "end")),
    ("languages", "languages", ("name", "level")),
)


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _source_ref(block_id: str) -> list[dict[str, Any]]:
    line = {
        "block-experience-1": 6,
        "block-experience-2": 10,
        "block-education-1": 14,
        "block-education-2": 18,
        "block-project-1": 22,
        "block-project-2": 26,
        "block-certification-1": 30,
        "block-contact": 34,
    }.get(block_id, 2)
    return [
        {
            "document_id": "doc-uploaded-cv",
            "locator": {"kind": "markdown_lines", "start": line, "end": line + 1},
        }
    ]


def _evidence(
    evidence_id: str,
    kind: str,
    text: str,
    block_id: str,
    *,
    title: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": evidence_id,
        "kind": kind,
        "text": text,
        "source_refs": _source_ref(block_id),
    }
    if title:
        item["title"] = title
    if start:
        item["start"] = start
    if end:
        item["end"] = end
    return item


def _baseline_document() -> dict[str, Any]:
    return {
        "source_documents": [
            {
                "id": "doc-uploaded-cv",
                "origin": "uploaded",
                "filename": "candidate.md",
                "media_type": "text/markdown",
                "checksum": _SOURCE_CHECKSUM,
                "parser": {"name": "fitcv-mock", "version": "1"},
            }
        ],
        "name": "Alex Morgan",
        "headline": "Data & Product Operations Specialist",
        "summary": "Data-focused operator who turns ambiguous business needs into measurable workflows, dashboards, and reliable delivery plans.",
        "contact": {
            "email": "alex.morgan@example.com",
            "phone": "+49 151 555 0184",
            "location": "Berlin, Germany",
            "linkedin": "",
            "github": "",
            "website": "",
        },
        "experiences": [
            {
                "id": "exp-northstar",
                "role": "Data Operations Working Student",
                "company": "Northstar Labs",
                "company_url": "",
                "location": "Berlin, Germany",
                "start": "2024-04",
                "end": "2026-07",
                "source_refs": _source_ref("block-experience-1"),
                "evidence": [
                    _evidence(
                        "ev-exp-quality",
                        "work_achievement",
                        "Built SQL quality checks, maintained Power BI reporting, and coordinated weekly delivery reviews with product and engineering.",
                        "block-experience-1",
                        title="Data quality and reporting",
                        start="2024-04",
                        end="2026-07",
                    ),
                ],
            },
            {
                "id": "exp-acme",
                "role": "Product Analytics Intern",
                "company": "Acme GmbH",
                "company_url": "",
                "location": "Munich, Germany",
                "start": "2023-06",
                "end": "2023-09",
                "source_refs": _source_ref("block-experience-2"),
                "evidence": [
                    _evidence(
                        "ev-exp-funnel",
                        "work_achievement",
                        "Analyzed funnel performance, automated weekly KPI reporting, and presented experiment results to product managers.",
                        "block-experience-2",
                        title="Funnel analytics",
                        start="2023-06",
                        end="2023-09",
                    )
                ],
            },
        ],
        "education": [
            {
                "id": "edu-msc",
                "institution": "Technical University of Berlin",
                "degree": "M.Sc. Information Systems",
                "field": "Information Systems",
                "location": "Berlin, Germany",
                "start": "2023-10",
                "end": "2026-07",
                "source_refs": _source_ref("block-education-1"),
                "evidence": [
                    _evidence(
                        "ev-edu-thesis",
                        "thesis",
                        "Compared deterministic CV parsing with controlled LLM normalization and evidence-aware skill extraction.",
                        "block-education-1",
                        title="Evidence-aware skill extraction",
                        start="2026-01",
                        end="2026-07",
                    ),
                    _evidence(
                        "ev-edu-seminars",
                        "seminar",
                        "Completed seminars in data governance, responsible AI, and product analytics.",
                        "block-education-1",
                        title="Applied seminars",
                        start="2025-04",
                        end="2025-07",
                    ),
                ],
            },
            {
                "id": "edu-bsc",
                "institution": "University of Mannheim",
                "degree": "B.Sc. Business Informatics",
                "field": "Business Informatics",
                "location": "Mannheim, Germany",
                "start": "2019-10",
                "end": "2023-07",
                "source_refs": _source_ref("block-education-2"),
                "evidence": [
                    _evidence(
                        "ev-edu-coursework",
                        "course",
                        "Applied databases, statistics, software engineering, and operations research to academic assignments.",
                        "block-education-2",
                        title="Applied coursework",
                        start="2019-10",
                        end="2023-07",
                    )
                ],
            },
        ],
        "projects": [
            {
                "id": "project-capstone",
                "name": "Graduate Analytics Capstone",
                "context": "University project with a nonprofit partner",
                "url": "",
                "start": "2025-01",
                "end": "2025-06",
                "source_refs": _source_ref("block-project-1"),
                "evidence": [
                    _evidence(
                        "ev-project-capstone",
                        "project_highlight",
                        "Designed a Python and SQL pipeline, defined KPI logic, and presented findings to non-technical stakeholders.",
                        "block-project-1",
                        title="Analytics delivery",
                        start="2025-01",
                        end="2025-06",
                    )
                ],
            },
            {
                "id": "project-fitcv",
                "name": "Evidence-aware CV Parser",
                "context": "Master thesis prototype",
                "url": "",
                "start": "2026-01",
                "end": "2026-07",
                "source_refs": _source_ref("block-project-2"),
                "evidence": [
                    _evidence(
                        "ev-project-parser",
                        "project_highlight",
                        "Combined deterministic document parsing with controlled LLM normalization and evidence tracking.",
                        "block-project-2",
                        title="Staged hybrid parser",
                        start="2026-01",
                        end="2026-07",
                    )
                ],
            },
        ],
        "achievements": [],
        "certifications": [
            {
                "id": "cert-powerbi",
                "name": "Microsoft Power BI Data Analyst Associate",
                "issuer": "Microsoft",
                "date": "2025-01",
                "expires": "",
                "credential_id": "",
                "url": "",
                "source_refs": _source_ref("block-certification-1"),
                "evidence": [
                    _evidence(
                        "ev-cert-powerbi",
                        "certification_proof",
                        "Earned Microsoft Power BI Data Analyst Associate certification.",
                        "block-certification-1",
                        title="Power BI certification",
                        start="2025-01",
                        end="2025-01",
                    )
                ],
            }
        ],
        "volunteering": [],
        "languages": [
            {"id": "lang-en", "name": "English", "level": "C1", "source_refs": _source_ref("block-contact")},
            {"id": "lang-de", "name": "German", "level": "B2", "source_refs": _source_ref("block-contact")},
        ],
        "interests": ["Data quality", "Product analytics"],
        "search_preferences": {
            "target_role": "Data & Product Operations",
            "location_types": ["hybrid", "remote"],
            "locations": ["Berlin"],
        },
    }


def _derived_document() -> dict[str, Any]:
    def claim(claim_id: str, name: str, refs: list[str], confidence: float) -> dict[str, Any]:
        return {
            "id": claim_id,
            "name": name,
            "origin": "llm_inferred",
            "confidence": confidence,
            "support_status": "supported",
            "evidence_refs": refs,
        }

    return {
        "skills": [
            claim("skill-sql", "SQL", ["ev-exp-quality", "ev-project-capstone"], 0.98),
            claim("skill-python", "Python", ["ev-project-capstone", "ev-project-parser"], 0.97),
            claim("skill-powerbi", "Power BI", ["ev-exp-quality", "ev-cert-powerbi"], 0.97),
            claim("skill-data-quality", "Data Quality", ["ev-exp-quality"], 0.94),
            claim("skill-product-analytics", "Product Analytics", ["ev-exp-funnel", "ev-edu-seminars"], 0.93),
            claim("skill-stakeholder", "Stakeholder Communication", ["ev-exp-quality", "ev-project-capstone"], 0.91),
        ],
        "role_families": [
            claim("role-family-data-operations", "Data Operations", ["ev-exp-quality"], 0.92),
            claim("role-family-product-analytics", "Product Analytics", ["ev-exp-funnel", "ev-edu-seminars"], 0.89),
        ],
        "domain_tags": [
            claim("domain-analytics", "Analytics", ["ev-project-capstone", "ev-exp-funnel"], 0.91),
            claim("domain-responsible-ai", "Responsible AI", ["ev-edu-thesis", "ev-project-parser"], 0.88),
        ],
        "responsibility_themes": [
            claim("theme-data-quality", "Data quality and reporting", ["ev-exp-quality"], 0.94),
            claim("theme-cross-functional", "Cross-functional delivery", ["ev-exp-quality", "ev-project-capstone"], 0.90),
        ],
    }


def _evidence_block_id(evidence_id: str) -> str:
    for section_id, prototype_key, _ in _PROTOTYPE_BASELINE_FIELDS:
        entries = _baseline_document().get(section_id, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if any(evidence["id"] == evidence_id for evidence in entry.get("evidence", [])):
                return _baseline_source_block_id(prototype_key, entry["id"], "evidence", evidence_id)
    raise KeyError(evidence_id)


def _baseline_source_block_id(
    prototype_key: str,
    entry_id: str,
    field_name: str,
    evidence_id: str = "",
) -> str:
    parts = ["block-baseline", prototype_key]
    if entry_id:
        parts.append(entry_id)
    parts.append("evidence" if evidence_id else field_name)
    if evidence_id:
        parts.append(evidence_id)
    return "-".join(parts)


def _prototype_source_blocks() -> dict[str, dict[str, Any]]:
    baseline = _baseline_document()
    blocks: dict[str, dict[str, Any]] = {}
    for section_index, (section_id, prototype_key, fields) in enumerate(_PROTOTYPE_BASELINE_FIELDS):
        entries = [("", baseline)] if section_id == "identity" else [("", baseline[section_id])] if section_id == "contact" else [(entry["id"], entry) for entry in baseline[section_id]]
        for entry_index, (entry_id, entry) in enumerate(entries):
            for field_index, field_name in enumerate(fields):
                position = 2 + section_index * 24 + entry_index * 8 + field_index
                block_id = _baseline_source_block_id(prototype_key, entry_id, field_name)
                blocks[block_id] = _source_block(block_id, str(entry.get(field_name) or ""), position)
            for evidence_index, evidence in enumerate(entry.get("evidence", [])):
                position = 2 + section_index * 24 + entry_index * 8 + evidence_index * 3
                block_id = _baseline_source_block_id(prototype_key, entry_id, "evidence", evidence["id"])
                blocks[block_id] = _source_block(block_id, evidence["text"], position)
    return blocks


def _source_block(block_id: str, text: str, line: int) -> dict[str, Any]:
    return {
        "source_block_id": block_id,
        "text": text,
        "kind": "markdown_lines",
        "locator": {"kind": "markdown_lines", "start": line, "end": line + 1},
        "source_document": {
            "source_document_id": "doc-uploaded-cv",
            "filename": "candidate.md",
            "media_type": "text/markdown",
            "checksum": _SOURCE_CHECKSUM,
        },
        "checksum": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


class CandidateProfileMockState:
    def __init__(self) -> None:
        self.attempts: dict[str, dict[str, Any]] = {}
        self.profiles: dict[str, dict[str, Any]] = {}
        self.idempotent_results: dict[tuple[str, str], dict[str, Any]] = {}
        self.counter = 0
        for index, seed in enumerate(CANDIDATE_PROFILE_SEEDS):
            canonical = self._canonical(_baseline_document(), _derived_document())
            filename = "-".join(seed["name"].lower().replace("&", "").split()) + ".yaml"
            canonical["source_documents"][0].update(
                filename=filename,
                media_type="application/yaml",
            )
            profile = self._profile_resource(
                profile_id=seed["candidate_profile_id"],
                profile_name=seed["name"],
                canonical=canonical,
                attempt_id=None,
            )
            if index == len(CANDIDATE_PROFILE_SEEDS) - 1:
                profile.update(lifecycle="archived", archived_at=_NOW)
                profile["capabilities"] = {
                    "inspect": True,
                    "archive": False,
                    "restore": True,
                    "use_for_run": False,
                }
            self.profiles[profile["profile_id"]] = profile

    @staticmethod
    def _canonical(baseline: dict[str, Any], derived: dict[str, Any]) -> dict[str, Any]:
        return {"schema_version": "candidate-profile.v2", **copy.deepcopy(baseline), **copy.deepcopy(derived)}

    @staticmethod
    def _review_annotations(stage: str) -> dict[str, Any]:
        if stage == "derived":
            annotations: dict[str, Any] = {}
            for section_id, entries in _derived_document().items():
                for entry in entries:
                    blocks = list(dict.fromkeys(_evidence_block_id(ref) for ref in entry["evidence_refs"]))
                    annotations[f"/{section_id}/{entry['id']}/name"] = {
                    "origin": "llm_inferred",
                    "source_block_ids": blocks,
                    "confidence": entry["confidence"],
                    "warnings": [],
                    "regenerable": True,
                    }
            return annotations
        baseline = _baseline_document()
        annotations: dict[str, Any] = {}
        prototype_keys = {section_id: prototype_key for section_id, prototype_key, _ in _PROTOTYPE_BASELINE_FIELDS}
        for section in candidate_profile_field_schema()["sections"]:
            section_id = section["id"]
            prototype_key = prototype_keys.get(section_id)
            if section.get("stage") != "baseline" or prototype_key is None:
                continue
            if section["shape"] == "object":
                for field_name in section.get("fields", {}):
                    path = f"/{field_name}" if section_id == "identity" else f"/{section_id}/{field_name}"
                    regenerable = path == "/summary"
                    annotations[path] = {
                        "origin": "llm_normalized" if regenerable else "deterministic",
                        "source_block_ids": [_baseline_source_block_id(prototype_key, "", field_name)],
                        "confidence": 0.9 if regenerable else 1.0,
                        "warnings": [],
                        "regenerable": regenerable,
                    }
                continue
            if section["shape"] == "collection":
                for entry in baseline[section_id]:
                    for field_name, field_meta in section["item"].items():
                        if field_name in {"id", "source_refs", "evidence"} or field_meta["shape"] == "collection":
                            continue
                        annotations[f"/{section_id}/{entry['id']}/{field_name}"] = {
                            "origin": "deterministic",
                            "source_block_ids": [_baseline_source_block_id(prototype_key, entry["id"], field_name)],
                            "confidence": 1.0,
                            "warnings": [],
                            "regenerable": False,
                        }
        for section_id in ("experiences", "education", "projects", "certifications"):
            for entry in baseline[section_id]:
                for evidence in entry.get("evidence", []):
                    annotations[f"/{section_id}/{entry['id']}/evidence/{evidence['id']}/text"] = {
                        "origin": "llm_normalized",
                        "source_block_ids": [_baseline_source_block_id(section_id, entry["id"], "evidence", evidence["id"])],
                        "confidence": 0.94,
                        "warnings": [],
                        "regenerable": True,
                    }
        return annotations

    @staticmethod
    def _source_blocks() -> dict[str, dict[str, Any]]:
        values = {
            "block-summary": "Data-focused operator who turns ambiguous business needs into measurable workflows, dashboards, and reliable delivery plans.",
            "block-experience-1": "Northstar Labs — Data Operations Working Student. Built SQL quality checks, maintained Power BI reporting, and coordinated weekly delivery reviews.",
            "block-experience-2": "Acme GmbH — Product Analytics Intern. Analyzed funnel performance and presented experiment results.",
            "block-education-1": "TU Berlin M.Sc. Information Systems. Thesis on evidence-aware skill extraction and seminars in responsible AI and product analytics.",
            "block-education-2": "University of Mannheim B.Sc. Business Informatics with applied databases, statistics, software engineering, and operations research.",
            "block-project-1": "Graduate Analytics Capstone using Python and SQL with a nonprofit partner.",
            "block-project-2": "Evidence-aware CV Parser combining deterministic parsing, controlled LLM normalization, and evidence tracking.",
            "block-certification-1": "Microsoft Power BI Data Analyst Associate certification.",
            "block-contact": "English C1. German B2.",
        }
        blocks = {
            block_id: {
                "source_block_id": block_id,
                "text": text,
                "kind": "markdown_lines",
                "locator": {"kind": "markdown_lines", "start": index * 4 + 1, "end": index * 4 + 2},
                "source_document": {
                    "source_document_id": "doc-uploaded-cv",
                    "filename": "candidate.md",
                    "media_type": "text/markdown",
                    "checksum": _SOURCE_CHECKSUM,
                },
                "checksum": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
            for index, (block_id, text) in enumerate(values.items())
        }
        blocks.update(_prototype_source_blocks())
        return blocks

    def _profile_resource(
        self,
        *,
        profile_id: str,
        profile_name: str,
        canonical: dict[str, Any],
        source_byte_length: int | None = None,
        attempt_id: str | None = None,
    ) -> dict[str, Any]:
        checksum = _fingerprint(canonical)
        source_document = dict((canonical.get("source_documents") or [{}])[0])
        original_filename = str(source_document.get("filename") or "candidate.md")
        return {
            "profile_id": profile_id,
            "profile_name": profile_name,
            "display_name": profile_name,
            "original_filename": original_filename,
            "creation": {
                "attempt_id": attempt_id,
                "source_format": Path(original_filename).suffix.lstrip(".").upper() or "YAML",
                "method": "staged-hybrid" if attempt_id else "legacy",
            },
            "creation_status": "succeeded",
            "lifecycle": "active",
            "created_at": _NOW,
            "updated_at": _NOW,
            "archived_at": None,
            "profile_revision_id": f"revision-{profile_id}",
            "failure": None,
            "related_run_count": 0,
            "capabilities": {
                "inspect": True,
                "archive": True,
                "restore": False,
                "use_for_run": True,
            },
            "revision": 1,
            "overview": copy.deepcopy(canonical),
            "input": {
                "original_filename": original_filename,
                "checksum": str(source_document.get("checksum") or _SOURCE_CHECKSUM),
                "byte_length": source_byte_length if source_byte_length is not None else len(_SOURCE_BYTES),
                "media_type": str(source_document.get("media_type") or "text/markdown"),
            },
            "profile": {
                "profile_revision_id": f"revision-{profile_id}",
                "revision": 1,
                "checksum": checksum,
                "schema_version": "candidate-profile.v2",
                "canonical": copy.deepcopy(canonical),
            },
        }

    @staticmethod
    def _capabilities(status: str) -> dict[str, Any]:
        return {
            "view_source": True,
            "review_baseline": status == "base_review",
            "approve_baseline": status == "base_review",
            "review_derived": status == "derived_review",
            "approve_derived": status == "derived_review",
            "confirm": status == "ready_to_confirm",
            "retry": status == "failed",
        }

    def _attempt_resource(self, attempt: dict[str, Any]) -> dict[str, Any]:
        return {
            "attempt_id": attempt["attempt_id"],
            "profile_name": attempt["profile_name"],
            "creation_status": attempt["status"],
            "revision": attempt["revision"],
            "source_document": {
                "source_document_id": "doc-uploaded-cv",
                "original_filename": attempt["filename"],
                "media_type": attempt["media_type"],
                "byte_length": len(attempt["content"]),
                "checksum": hashlib.sha256(attempt["content"]).hexdigest(),
                "source_available": True,
            },
            "processing": {"stage": None, "claim_id": None, "attempt": 1, "lease_expires_at": None},
            "source_purge_after": "2026-09-01T12:00:00+00:00",
            "fingerprints": {
                "extraction": attempt["extraction_fingerprint"],
                "baseline_draft": attempt["baseline_fingerprint"],
                "approved_baseline": attempt.get("approved_baseline_fingerprint"),
                "derived_draft": attempt["derived_fingerprint"],
                "approved_derived": attempt.get("approved_derived_fingerprint"),
                "confirmation": attempt.get("confirmation_fingerprint"),
            },
            "approval_timestamps": {
                "baseline": attempt.get("baseline_approved_at"),
                "derived": attempt.get("derived_approved_at"),
            },
            "failure": attempt.get("failure"),
            "next_action": attempt["next_action"],
            "capabilities": self._capabilities(attempt["status"]),
            "created_at": _NOW,
            "updated_at": _NOW,
        }

    def query_attempts(self, **kwargs: Any) -> dict[str, Any]:
        search = str(kwargs.get("search") or "").lower()
        status = str(kwargs.get("status") or "")
        items = [self._attempt_resource(attempt) for attempt in self.attempts.values()]
        if search:
            items = [item for item in items if search in item["profile_name"].lower()]
        if status:
            items = [item for item in items if item["creation_status"] == status]
        return {"items": items, "total": len(items)}

    def create_attempt(self, **kwargs: Any) -> dict[str, Any]:
        key = ("create", str(kwargs["idempotency_key"]))
        if key in self.idempotent_results:
            return copy.deepcopy(self.idempotent_results[key])
        profile_name = str(kwargs.get("profile_name") or "").strip()
        filename = Path(str(kwargs.get("original_filename") or "")).name
        content = bytes(kwargs.get("content") or b"")
        if not profile_name:
            raise ValueError("candidate_profile_name_required")
        if Path(filename).suffix.lower() not in {".md", ".docx", ".yaml"}:
            raise ValueError("candidate_profile_file_type_invalid")
        if not content:
            raise ValueError("candidate_profile_file_empty")
        self.counter += 1
        attempt_id = f"attempt-mock-{self.counter}"
        baseline = _baseline_document()
        baseline["source_documents"][0]["filename"] = filename
        baseline["source_documents"][0]["media_type"] = str(kwargs.get("media_type") or "application/octet-stream")
        baseline["source_documents"][0]["checksum"] = hashlib.sha256(content).hexdigest()
        derived = _derived_document()
        attempt = {
            "attempt_id": attempt_id,
            "profile_name": profile_name,
            "filename": filename,
            "media_type": str(kwargs.get("media_type") or "application/octet-stream"),
            "content": content,
            "status": "base_review",
            "next_action": "review_baseline",
            "revision": 1,
            "baseline": baseline,
            "derived": derived,
            "extraction_fingerprint": _fingerprint(self._source_blocks()),
            "baseline_fingerprint": _fingerprint(baseline),
            "derived_fingerprint": _fingerprint(derived),
            "source_blocks": self._source_blocks(),
        }
        self.attempts[attempt_id] = attempt
        resource = self._attempt_resource(attempt)
        self.idempotent_results[key] = copy.deepcopy(resource)
        return resource

    def get_attempt(self, attempt_id: str) -> dict[str, Any] | None:
        attempt = self.attempts.get(attempt_id)
        return self._attempt_resource(attempt) if attempt else None

    def get_source(self, attempt_id: str) -> dict[str, Any] | None:
        attempt = self.attempts.get(attempt_id)
        if not attempt:
            return None
        return {
            "content": attempt["content"],
            "filename": attempt["filename"],
            "media_type": attempt["media_type"],
            "checksum": hashlib.sha256(attempt["content"]).hexdigest(),
        }

    def get_source_block(self, attempt_id: str, source_block_id: str) -> dict[str, Any] | None:
        attempt = self.attempts.get(attempt_id)
        if not attempt:
            return None
        return copy.deepcopy(attempt["source_blocks"].get(source_block_id))

    @staticmethod
    def _assert_revision(attempt: dict[str, Any], expected_revision: int) -> None:
        if int(expected_revision) != int(attempt["revision"]):
            raise ValueError("candidate_profile_revision_conflict")

    @staticmethod
    def _list_item(items: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
        for item in items:
            if isinstance(item, dict) and str(item.get("id")) == item_id:
                return item
        raise ValueError("candidate_profile_field_not_found")

    def _apply_operation(self, document: dict[str, Any], operation: dict[str, Any]) -> None:
        segments = [segment for segment in str(operation["path"]).split("/") if segment]
        if not segments:
            raise ValueError("candidate_profile_field_not_found")
        action = str(operation["operation"])
        target: Any = document
        for segment in segments[:-1]:
            if isinstance(target, list):
                target = self._list_item(target, segment)
            elif isinstance(target, dict):
                target = target.get(segment)
            else:
                target = None
            if target is None:
                raise ValueError("candidate_profile_field_not_found")
        final = segments[-1]
        if isinstance(target, list):
            if action == "add":
                target.append(copy.deepcopy(operation.get("value")))
                return
            if final.isdigit() and (not target or not isinstance(target[0], dict)):
                index = int(final)
                if index >= len(target):
                    raise ValueError("candidate_profile_field_not_found")
                if action == "replace":
                    target[index] = copy.deepcopy(operation.get("value"))
                    return
                if action == "remove":
                    target.pop(index)
                    return
            item = self._list_item(target, final)
            if action == "remove":
                target.remove(item)
                return
            raise ValueError("candidate_profile_field_not_found")
        if not isinstance(target, dict):
            raise ValueError("candidate_profile_field_not_found")
        if action in {"add", "replace"}:
            target[final] = copy.deepcopy(operation.get("value"))
        elif action == "remove":
            target.pop(final, None)

    def get_review(self, attempt_id: str, stage: str) -> dict[str, Any] | None:
        attempt = self.attempts.get(attempt_id)
        if not attempt:
            return None
        if stage == "derived" and attempt["status"] == "base_review":
            raise ValueError("candidate_profile_invalid_transition")
        document = attempt[stage]
        return {
            "attempt_id": attempt_id,
            "stage": stage,
            "revision": attempt["revision"],
            "fingerprint": attempt[f"{stage}_fingerprint"],
            "document": copy.deepcopy(document),
            "annotations": self._review_annotations(stage),
            "validation": {"field_errors": []},
            "capabilities": {
                "patch": True,
                "regenerate_all": True,
                "approve": attempt["status"] == ("base_review" if stage == "baseline" else "derived_review"),
            },
        }

    def patch_review(self, attempt_id: str, stage: str, **kwargs: Any) -> dict[str, Any]:
        attempt = self.attempts.get(attempt_id)
        if not attempt:
            raise ValueError("candidate_profile_attempt_not_found")
        self._assert_revision(attempt, int(kwargs["expected_revision"]))
        key = (f"patch-{stage}", str(kwargs["idempotency_key"]))
        if key in self.idempotent_results:
            return copy.deepcopy(self.idempotent_results[key])
        for operation in kwargs.get("operations") or []:
            self._apply_operation(attempt[stage], operation)
        attempt["revision"] += 1
        attempt[f"{stage}_fingerprint"] = _fingerprint(attempt[stage])
        if stage == "baseline":
            attempt.pop("approved_baseline_fingerprint", None)
            attempt.pop("approved_derived_fingerprint", None)
            attempt.pop("baseline_approved_at", None)
            attempt.pop("derived_approved_at", None)
            attempt["status"] = "base_review"
            attempt["next_action"] = "review_baseline"
        else:
            attempt.pop("approved_derived_fingerprint", None)
            attempt.pop("derived_approved_at", None)
            attempt["status"] = "derived_review"
            attempt["next_action"] = "review_derived"
        resource = self.get_review(attempt_id, stage)
        assert resource is not None
        self.idempotent_results[key] = copy.deepcopy(resource)
        return resource

    def regenerate_review(self, attempt_id: str, stage: str, **kwargs: Any) -> dict[str, Any]:
        attempt = self.attempts.get(attempt_id)
        if not attempt:
            raise ValueError("candidate_profile_attempt_not_found")
        self._assert_revision(attempt, int(kwargs["expected_revision"]))
        targets = [str(target) for target in kwargs.get("targets") or []]
        annotations = self._review_annotations(stage)
        if targets != ["*"]:
            for target in targets:
                if not bool((annotations.get(target) or {}).get("regenerable")):
                    raise ValueError("candidate_profile_field_not_regenerable")
        if stage == "baseline":
            attempt["baseline"]["summary"] = "Transforms product data into reliable decisions and measurable outcomes."
        else:
            attempt["derived"]["skills"][0]["confidence"] = 0.99
        attempt["revision"] += 1
        attempt[f"{stage}_fingerprint"] = _fingerprint(attempt[stage])
        attempt["status"] = "base_review" if stage == "baseline" else "derived_review"
        attempt["next_action"] = "review_baseline" if stage == "baseline" else "review_derived"
        return self._attempt_resource(attempt)

    def approve_review(self, attempt_id: str, stage: str, **kwargs: Any) -> dict[str, Any]:
        attempt = self.attempts.get(attempt_id)
        if not attempt:
            raise ValueError("candidate_profile_attempt_not_found")
        self._assert_revision(attempt, int(kwargs["expected_revision"]))
        if str(kwargs["expected_fingerprint"]) != attempt[f"{stage}_fingerprint"]:
            raise ValueError("candidate_profile_fingerprint_conflict")
        if stage == "derived" and str(kwargs["expected_baseline_fingerprint"]) != attempt.get("approved_baseline_fingerprint"):
            raise ValueError("candidate_profile_fingerprint_conflict")
        attempt["revision"] += 1
        attempt[f"approved_{stage}_fingerprint"] = attempt[f"{stage}_fingerprint"]
        attempt[f"{stage}_approved_at"] = _NOW
        if stage == "baseline":
            attempt["status"] = "derived_review"
            attempt["next_action"] = "review_derived"
        else:
            attempt["status"] = "ready_to_confirm"
            attempt["next_action"] = "confirm"
        return self._attempt_resource(attempt)

    def confirmation(self, attempt_id: str) -> dict[str, Any] | None:
        attempt = self.attempts.get(attempt_id)
        if not attempt:
            return None
        if attempt["status"] not in {"ready_to_confirm", "succeeded"}:
            raise ValueError("candidate_profile_invalid_transition")
        canonical = self._canonical(attempt["baseline"], attempt["derived"])
        checksum = _fingerprint(canonical)
        fingerprint = _fingerprint(
            {
                "profile_name": attempt["profile_name"],
                "baseline": attempt["approved_baseline_fingerprint"],
                "derived": attempt["approved_derived_fingerprint"],
                "checksum": checksum,
            }
        )
        attempt["confirmation_fingerprint"] = fingerprint
        return {
            "attempt_id": attempt_id,
            "revision": attempt["revision"],
            "profile_name": attempt["profile_name"],
            "fingerprint": fingerprint,
            "approval_fingerprints": {
                "baseline": attempt["approved_baseline_fingerprint"],
                "derived": attempt["approved_derived_fingerprint"],
            },
            "profile": {
                "checksum": checksum,
                "schema_version": "candidate-profile.v2",
                "canonical": canonical,
            },
            "readiness": {"ready": True, "blocking_errors": []},
            "warnings": [],
        }

    def confirm(self, attempt_id: str, **kwargs: Any) -> dict[str, Any]:
        attempt = self.attempts.get(attempt_id)
        if not attempt:
            raise ValueError("candidate_profile_attempt_not_found")
        self._assert_revision(attempt, int(kwargs["expected_revision"]))
        confirmation = self.confirmation(attempt_id)
        assert confirmation is not None
        if str(kwargs["expected_baseline_fingerprint"]) != confirmation["approval_fingerprints"]["baseline"]:
            raise ValueError("candidate_profile_fingerprint_conflict")
        if str(kwargs["expected_derived_fingerprint"]) != confirmation["approval_fingerprints"]["derived"]:
            raise ValueError("candidate_profile_fingerprint_conflict")
        if str(kwargs["expected_confirmation_fingerprint"]) != confirmation["fingerprint"]:
            raise ValueError("candidate_profile_fingerprint_conflict")
        if attempt.get("profile_id"):
            return copy.deepcopy(self.profiles[attempt["profile_id"]])
        profile_id = f"profile-mock-{len(self.profiles) + 1}"
        profile = self._profile_resource(
            profile_id=profile_id,
            profile_name=attempt["profile_name"],
            canonical=confirmation["profile"]["canonical"],
            source_byte_length=len(attempt["content"]),
            attempt_id=attempt_id,
        )
        self.profiles[profile_id] = profile
        attempt["profile_id"] = profile_id
        attempt["status"] = "succeeded"
        attempt["next_action"] = "view_profile"
        return copy.deepcopy(profile)

    def retry(self, attempt_id: str, **kwargs: Any) -> dict[str, Any]:
        attempt = self.attempts.get(attempt_id)
        if not attempt:
            raise ValueError("candidate_profile_attempt_not_found")
        self._assert_revision(attempt, int(kwargs["expected_revision"]))
        if attempt["status"] != "failed":
            raise ValueError("candidate_profile_invalid_transition")
        attempt["revision"] += 1
        attempt["status"] = "base_review"
        attempt["next_action"] = "review_baseline"
        attempt["failure"] = None
        return self._attempt_resource(attempt)

    def query_profiles(self, **kwargs: Any) -> dict[str, Any]:
        view = str(kwargs.get("view") or "active")
        search = str(kwargs.get("search") or "").lower()
        items = [copy.deepcopy(profile) for profile in self.profiles.values() if profile["lifecycle"] == view]
        if search:
            items = [item for item in items if search in item["display_name"].lower()]
        return {
            "items": items,
            "total": len(items),
            "page": int(kwargs.get("page") or 1),
            "page_size": int(kwargs.get("page_size") or 20),
            "active_count": sum(profile["lifecycle"] == "active" for profile in self.profiles.values()),
            "archived_count": sum(profile["lifecycle"] == "archived" for profile in self.profiles.values()),
        }

    def get_profile(self, profile_id: str) -> dict[str, Any] | None:
        return copy.deepcopy(self.profiles.get(profile_id))

    def get_profile_for_run(self, profile_id: str) -> dict[str, Any] | None:
        profile = self.profiles.get(profile_id)
        if not profile:
            return None
        return {
            "candidate_profile_id": profile_id,
            "name": profile["profile_name"],
            "profile": copy.deepcopy(profile["profile"]["canonical"]),
            "revision": profile["revision"],
            "is_active": profile["lifecycle"] == "active",
        }

    def transition_profile(self, profile_id: str, **kwargs: Any) -> dict[str, Any]:
        profile = self.profiles.get(profile_id)
        if not profile:
            raise ValueError("profile_not_found")
        if int(kwargs["expected_revision"]) != int(profile["revision"]):
            raise ValueError("candidate_profile_revision_conflict")
        lifecycle = str(kwargs["lifecycle"])
        profile["lifecycle"] = lifecycle
        profile["archived_at"] = _NOW if lifecycle == "archived" else None
        profile["revision"] += 1
        profile["capabilities"] = {
            "inspect": True,
            "archive": lifecycle == "active",
            "restore": lifecycle == "archived",
            "use_for_run": lifecycle == "active",
        }
        return copy.deepcopy(profile)


def create_candidate_profile_mock_app():
    root = Path(tempfile.mkdtemp(prefix="fitcv-candidate-profile-mock-"))
    os.environ["FITCV_CP_SQLITE_PATH"] = str(root / "mock.sqlite3")
    app = create_app(redis_url="redis://localhost:6379/0")
    state = CandidateProfileMockState()
    store = app.state.run_store
    store.query_candidate_profile_creation_attempts_fn = state.query_attempts
    store.create_candidate_profile_creation_attempt_fn = state.create_attempt
    store.get_candidate_profile_creation_attempt_fn = state.get_attempt
    store.get_candidate_profile_source_fn = state.get_source
    store.get_candidate_profile_source_block_fn = state.get_source_block
    store.get_candidate_profile_review_fn = state.get_review
    store.patch_candidate_profile_review_fn = state.patch_review
    store.regenerate_candidate_profile_review_fn = state.regenerate_review
    store.approve_candidate_profile_review_fn = state.approve_review
    store.get_candidate_profile_confirmation_fn = state.confirmation
    store.confirm_candidate_profile_creation_attempt_fn = state.confirm
    store.retry_candidate_profile_creation_attempt_fn = state.retry
    store.query_candidate_profiles_fn = state.query_profiles
    store.get_candidate_profile_detail_fn = state.get_profile
    store.get_candidate_profile_fn = state.get_profile_for_run
    store.query_candidate_profile_runs_fn = lambda _profile_id, **_kwargs: {"items": [], "total": 0}
    store.transition_candidate_profile_lifecycle_fn = state.transition_profile
    app.state.templates.env.globals["local_mode"] = True
    if not any(route.path == "/admin/llm-configuration" for route in app.routes):
        llm_configuration = {
            "revision": 1,
            "default_model_ref": "model-openai-gpt-4-1-mini",
            "tasks": {
                task_id: {"model_ref": None, "timeout_seconds": 120, "temperature": 0.2}
                for task_id in (
                    "candidate_profile_base_mapping",
                    "candidate_profile_derived_claims",
                    "enrich_extraction",
                    "ranking_ai_score",
                    "cv_generation_structured_write",
                    "synonym_triage_recommendation",
                )
            },
            "eligible_models": [
                {
                    "model_record_id": "model-openai-gpt-4-1-mini",
                    "provider_display_name": "OpenAI",
                    "model_id": "gpt-4.1-mini",
                }
            ],
        }

        @app.get("/llm-configuration")
        def get_mock_llm_configuration() -> dict[str, Any]:
            return {"data": copy.deepcopy(llm_configuration)}

        @app.patch("/llm-configuration")
        async def patch_mock_llm_configuration(request: Request) -> JSONResponse:
            body = await request.json()
            if body.get("expected_revision") != llm_configuration["revision"]:
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": {
                            "code": "llm_configuration_revision_conflict",
                            "message": "LLM Configuration changed since last read.",
                        }
                    },
                )
            if "default_model_ref" in body:
                llm_configuration["default_model_ref"] = body["default_model_ref"]
            for task_id, changes in body.get("tasks", {}).items():
                llm_configuration["tasks"][task_id].update(changes)
            llm_configuration["revision"] += 1
            return JSONResponse({"data": copy.deepcopy(llm_configuration)})

        @app.get("/admin/llm-configuration", response_class=HTMLResponse)
        def admin_mock_llm_configuration(request: Request) -> HTMLResponse:
            return app.state.templates.TemplateResponse(
                request=request,
                name="llm_configuration.html",
                context={
                    "configuration": llm_configuration,
                    "eligible_model_ids": {"model-openai-gpt-4-1-mini"},
                },
            )
    app.state.candidate_profile_mock_state = state
    return app


app = create_candidate_profile_mock_app()
