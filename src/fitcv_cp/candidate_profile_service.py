"""Store-neutral staged Candidate Profile processing."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable

from fitcv.candidate import (
    CANDIDATE_PROFILE_V2_FIELD_REGISTRY,
    canonical_candidate_checksum,
    validate_candidate_profile_v2,
)
from fitcv.candidate_ingest import CandidateIngestError, CandidateIngestResult, ingest_candidate_source
from fitcv.config import get_prompt_replacement, load_prompt_task_registry
from fitcv.llm_runtime import (
    LlmRuntimeResult,
    LlmTaskRequest,
    LlmValidationResult,
    execute_llm_task,
    parse_llm_json_object,
    project_llm_runtime_evidence,
)
from fitcv.prompts import render_prompt


_BASELINE_COLLECTIONS = tuple(
    section["id"]
    for section in CANDIDATE_PROFILE_V2_FIELD_REGISTRY["sections"]
    if section.get("stage") == "baseline" and section.get("shape") == "collection"
)
_BASELINE_COLLECTION_FIELDS = {
    section["id"]: frozenset(section["item"]) - {"id", "source_refs", "evidence"}
    for section in CANDIDATE_PROFILE_V2_FIELD_REGISTRY["sections"]
    if section.get("stage") == "baseline" and section.get("shape") == "collection"
}
_BASELINE_REGENERABLE_SCALAR_PATHS = frozenset(
    f"/{field_id}" if section["id"] == "identity" else f"/{section['id']}/{field_id}"
    for section in CANDIDATE_PROFILE_V2_FIELD_REGISTRY["sections"]
    if section.get("stage") == "baseline" and section.get("shape") == "object"
    for field_id, field in section["fields"].items()
    if field.get("regenerable")
)
_DERIVED_COLLECTIONS = tuple(
    section["id"]
    for section in CANDIDATE_PROFILE_V2_FIELD_REGISTRY["sections"]
    if section.get("stage") == "derived"
)
_EVIDENCE_KINDS = frozenset(CANDIDATE_PROFILE_V2_FIELD_REGISTRY["evidence_kinds"])
_COLLECTION_ID_PREFIX = {
    "experiences": "exp",
    "education": "edu",
    "projects": "proj",
    "achievements": "ach",
    "certifications": "cert",
    "volunteering": "vol",
    "languages": "lang",
}
_DERIVED_ID_PREFIX = {
    "skills": "skill",
    "role_families": "role",
    "domain_tags": "domain",
    "responsibility_themes": "responsibility",
}
_BASELINE_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "proposals": {"type": "array", "items": {"type": "object"}},
        "collections": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["proposals", "collections"],
}
_DERIVED_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"claims": {"type": "array", "items": {"type": "object"}}},
    "required": ["claims"],
}
_REGENERATION_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"proposals": {"type": "array", "items": {"type": "object"}}},
    "required": ["proposals"],
}
_LlmRunner = Callable[..., LlmRuntimeResult]


class CandidateProfileServiceError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        last_valid_document: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.last_valid_document = copy.deepcopy(last_valid_document)


@dataclass(frozen=True)
class CandidateProfileStageResult:
    document: dict[str, Any]
    annotations: dict[str, Any]
    fingerprint: str
    runtime_evidence: dict[str, Any] | None
    llm_called: bool
    baseline_fingerprint: str | None = None
    derived_seed: dict[str, Any] | None = None


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _render_task_prompt(task_id: str, payload: Any) -> str:
    prompt_id = load_prompt_task_registry()[task_id]["prompt_id"]
    return render_prompt(
        prompt_id,
        {"payload": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
        replacement_text=get_prompt_replacement(task_id),
    ).text


def _stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{_fingerprint(value)[:16]}"


def _empty_baseline(source_document: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_documents": [copy.deepcopy(source_document)],
        "name": "",
        "headline": None,
        "summary": None,
        "contact": {},
        **{section: [] for section in _BASELINE_COLLECTIONS},
        "interests": [],
        "search_preferences": {},
    }


def _split_canonical(profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    baseline = {
        "source_documents": copy.deepcopy(profile.get("source_documents") or []),
        "name": profile.get("name"),
        "headline": profile.get("headline"),
        "summary": profile.get("summary"),
        "contact": copy.deepcopy(profile.get("contact") or {}),
        **{section: copy.deepcopy(profile.get(section) or []) for section in _BASELINE_COLLECTIONS},
        "interests": copy.deepcopy(profile.get("interests") or []),
        "search_preferences": copy.deepcopy(profile.get("search_preferences") or {}),
    }
    derived = {section: copy.deepcopy(profile.get(section) or []) for section in _DERIVED_COLLECTIONS}
    return baseline, derived


def _annotation(
    *,
    origin: str,
    source_block_ids: list[str],
    confidence: float,
    regenerable: bool,
) -> dict[str, Any]:
    return {
        "origin": origin,
        "source_block_ids": list(source_block_ids),
        "confidence": confidence,
        "warnings": [],
        "regenerable": regenerable,
    }


def _canonical_annotations(document: dict[str, Any]) -> dict[str, Any]:
    annotations: dict[str, Any] = {}
    for field in ("name", "headline", "summary"):
        if field in document:
            annotations[f"/{field}"] = _annotation(origin="deterministic", source_block_ids=[], confidence=1.0, regenerable=False)
    for field in (document.get("contact") or {}):
        annotations[f"/contact/{field}"] = _annotation(origin="deterministic", source_block_ids=[], confidence=1.0, regenerable=False)
    for section in _BASELINE_COLLECTIONS:
        for entry in document.get(section) or []:
            entry_id = str(entry.get("id") or "")
            for field, value in entry.items():
                if field in {"id", "source_refs", "evidence"} or isinstance(value, (dict, list)):
                    continue
                annotations[f"/{section}/{entry_id}/{field}"] = _annotation(origin="deterministic", source_block_ids=[], confidence=1.0, regenerable=False)
            for evidence in entry.get("evidence") or []:
                evidence_id = str(evidence.get("id") or "")
                annotations[f"/{section}/{entry_id}/evidence/{evidence_id}/text"] = _annotation(origin="deterministic", source_block_ids=[], confidence=1.0, regenerable=False)
    return annotations


def _runtime_failure(result: LlmRuntimeResult, document: dict[str, Any]) -> CandidateProfileServiceError:
    failure = result.failure
    if failure is not None and failure.stage in {"routing", "adapter"}:
        return CandidateProfileServiceError(
            "candidate_profile_llm_unavailable",
            failure.message,
            retryable=failure.retryable,
            last_valid_document=document,
        )
    return CandidateProfileServiceError(
        "candidate_profile_llm_output_invalid",
        failure.message if failure is not None else "LLM output is invalid",
        retryable=True,
        last_valid_document=document,
    )


def _validation(errors: list[str]) -> LlmValidationResult:
    return LlmValidationResult(valid=not errors, errors=errors, details={})


def _block_refs(block_ids: list[str], blocks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for block_id in block_ids:
        block = blocks.get(block_id)
        if block is None:
            continue
        ref = {"document_id": block["document_id"], "locator": copy.deepcopy(block["locator"])}
        key = json.dumps(ref, sort_keys=True, separators=(",", ":"))
        if key not in seen:
            seen.add(key)
            refs.append(ref)
    return refs


def _validate_baseline_payload(value: Any, block_ids: set[str]) -> LlmValidationResult:
    errors: list[str] = []
    if not isinstance(value, dict):
        return _validation(["response must be a mapping"])
    proposals = value.get("proposals")
    collections = value.get("collections")
    if not isinstance(proposals, list) or not isinstance(collections, list):
        return _validation(["proposals and collections must be lists"])
    allowed_scalar_paths = {"/name", "/headline", "/summary", *{f"/contact/{field}" for field in ("email", "phone", "location", "linkedin", "github", "website")}}
    for proposal in proposals:
        if not isinstance(proposal, dict) or proposal.get("path") not in allowed_scalar_paths:
            errors.append("invalid baseline proposal path")
            continue
        refs = proposal.get("source_block_ids")
        if not isinstance(refs, list) or not refs or not set(refs) <= block_ids:
            errors.append("baseline proposal requires valid source_block_ids")
    for collection in collections:
        if not isinstance(collection, dict) or collection.get("section") not in _BASELINE_COLLECTIONS:
            errors.append("invalid baseline collection")
            continue
        fields = collection.get("fields")
        if not isinstance(fields, dict):
            errors.append("baseline collection fields must be a mapping")
            continue
        if set(fields) - _BASELINE_COLLECTION_FIELDS[str(collection["section"])]:
            errors.append("unsupported baseline collection field")
        refs = collection.get("source_block_ids")
        if not isinstance(refs, list) or not refs or not set(refs) <= block_ids:
            errors.append("baseline collection requires valid source_block_ids")
    return _validation(errors)


def _run_llm(
    request: LlmTaskRequest,
    validator: Callable[[Any], LlmValidationResult],
    runner: _LlmRunner | None,
    document: dict[str, Any],
) -> LlmRuntimeResult:
    result = (runner or execute_llm_task)(request, parser=parse_llm_json_object, validator=validator)
    if result.status != "succeeded":
        raise _runtime_failure(result, document)
    validation = validator(result.parsed_value)
    if not validation.valid:
        raise CandidateProfileServiceError(
            "candidate_profile_llm_output_invalid",
            "; ".join(validation.errors),
            retryable=True,
            last_valid_document=document,
        )
    return result


def _apply_scalar_proposal(
    document: dict[str, Any],
    proposal: dict[str, Any],
    annotations: dict[str, Any],
) -> None:
    path = str(proposal["path"])
    segments = [segment for segment in path.split("/") if segment]
    if segments[0] == "contact":
        document.setdefault("contact", {})[segments[1]] = copy.deepcopy(proposal.get("value"))
    else:
        document[segments[0]] = copy.deepcopy(proposal.get("value"))
    annotations[path] = _annotation(
        origin="llm_normalized",
        source_block_ids=list(proposal.get("source_block_ids") or []),
        confidence=float(proposal.get("confidence", 0.0)),
        regenerable=path in _BASELINE_REGENERABLE_SCALAR_PATHS,
    )


def _apply_collection_proposal(
    document: dict[str, Any],
    proposal: dict[str, Any],
    annotations: dict[str, Any],
    blocks: dict[str, dict[str, Any]],
) -> None:
    section = str(proposal["section"])
    block_ids = list(proposal.get("source_block_ids") or [])
    fields = copy.deepcopy(proposal.get("fields") or {})
    entry_id = _stable_id(_COLLECTION_ID_PREFIX[section], [section, fields, block_ids])
    entry = {"id": entry_id, **fields, "source_refs": _block_refs(block_ids, blocks)}
    evidence_items: list[dict[str, Any]] = []
    for index, raw in enumerate(proposal.get("evidence") or []):
        if not isinstance(raw, dict):
            continue
        evidence_block_ids = list(raw.get("source_block_ids") or block_ids)
        text = str(raw.get("text") or "").strip()
        kind = str(raw.get("kind") or "")
        if not text or kind not in _EVIDENCE_KINDS or not set(evidence_block_ids) <= set(blocks):
            continue
        evidence_id = _stable_id(f"ev_{entry_id}", [index, kind, text, evidence_block_ids])
        evidence = {
            "id": evidence_id,
            "kind": kind,
            "text": text,
            "source_refs": _block_refs(evidence_block_ids, blocks),
        }
        if raw.get("title"):
            evidence["title"] = str(raw["title"])
        evidence_items.append(evidence)
        annotations[f"/{section}/{entry_id}/evidence/{evidence_id}/text"] = _annotation(
            origin="llm_normalized",
            source_block_ids=evidence_block_ids,
            confidence=float(raw.get("confidence", proposal.get("confidence", 0.0))),
            regenerable=True,
        )
    if section != "languages":
        entry["evidence"] = evidence_items
    document.setdefault(section, []).append(entry)
    for field in fields:
        annotations[f"/{section}/{entry_id}/{field}"] = _annotation(
            origin="llm_normalized",
            source_block_ids=block_ids,
            confidence=float(proposal.get("confidence", 0.0)),
            regenerable=False,
        )


def build_baseline_review(
    ingest: CandidateIngestResult,
    *,
    llm_runner: _LlmRunner | None = None,
) -> CandidateProfileStageResult:
    if ingest.profile is not None:
        document, derived_seed = _split_canonical(ingest.profile)
        return CandidateProfileStageResult(
            document=document,
            annotations=_canonical_annotations(document),
            fingerprint=_fingerprint(document),
            runtime_evidence=None,
            llm_called=False,
            derived_seed=derived_seed,
        )

    document = _empty_baseline(ingest.source_document)
    annotations: dict[str, Any] = {}
    resolved: set[str] = set()
    for block in ingest.source_blocks:
        if block["kind"] == "heading" and not document["name"]:
            document["name"] = block["text"]
            resolved.add(block["block_id"])
            annotations["/name"] = _annotation(
                origin="deterministic",
                source_block_ids=[block["block_id"]],
                confidence=1.0,
                regenerable=False,
            )
    unresolved = [block for block in ingest.source_blocks if block["block_id"] not in resolved]
    if not unresolved:
        return CandidateProfileStageResult(document, annotations, _fingerprint(document), None, False)

    block_lookup = {block["block_id"]: block for block in unresolved}
    request = LlmTaskRequest(
        routing_part="candidate_profile_base_mapping",
        prompt=_render_task_prompt("candidate_profile_base_mapping", {"source_blocks": unresolved}),
        response_mode="json_schema",
        instructions="Map only observable source content. Never invent IDs, facts, evidence text, or source locations.",
        schema_name="candidate_profile_base_mapping",
        schema=_BASELINE_RESPONSE_SCHEMA,
    )
    result = _run_llm(
        request,
        lambda value: _validate_baseline_payload(value, set(block_lookup)),
        llm_runner,
        document,
    )
    value = result.parsed_value
    for proposal in value["proposals"]:
        _apply_scalar_proposal(document, proposal, annotations)
    for proposal in value["collections"]:
        _apply_collection_proposal(document, proposal, annotations, block_lookup)
    return CandidateProfileStageResult(
        document=document,
        annotations=annotations,
        fingerprint=_fingerprint(document),
        runtime_evidence=project_llm_runtime_evidence(result),
        llm_called=True,
    )


def _evidence_ids(baseline: dict[str, Any]) -> set[str]:
    return {
        str(evidence.get("id") or "")
        for section in _BASELINE_COLLECTIONS
        for entry in baseline.get(section) or []
        if isinstance(entry, dict)
        for evidence in entry.get("evidence") or []
        if isinstance(evidence, dict) and evidence.get("id")
    }


def _validate_derived_payload(value: Any, evidence_ids: set[str]) -> LlmValidationResult:
    errors: list[str] = []
    if not isinstance(value, dict) or not isinstance(value.get("claims"), list):
        return _validation(["claims must be a list"])
    for claim in value["claims"]:
        if not isinstance(claim, dict) or claim.get("section") not in _DERIVED_COLLECTIONS:
            errors.append("invalid derived claim section")
            continue
        if not str(claim.get("name") or "").strip():
            errors.append("derived claim requires name")
        refs = claim.get("evidence_refs")
        if not isinstance(refs, list) or not refs or not set(refs) <= evidence_ids:
            errors.append("derived claim requires valid evidence_refs")
        confidence = claim.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            errors.append("derived claim confidence must be between 0 and 1")
    return _validation(errors)


def build_derived_review(
    approved_baseline: dict[str, Any],
    *,
    llm_runner: _LlmRunner | None = None,
    seed_document: dict[str, Any] | None = None,
) -> CandidateProfileStageResult:
    if approved_baseline.get("stage") != "baseline":
        raise CandidateProfileServiceError("candidate_profile_transition_invalid", "Approved baseline is required")
    baseline = copy.deepcopy(approved_baseline["document"])
    baseline_fingerprint = str(approved_baseline["fingerprint"])
    evidence_ids = _evidence_ids(baseline)
    if seed_document is not None:
        validation = _validate_derived_payload(
            {"claims": [{"section": section, **claim} for section in _DERIVED_COLLECTIONS for claim in seed_document.get(section) or []]},
            evidence_ids,
        )
        if not validation.valid:
            raise CandidateProfileServiceError("candidate_profile_reference_invalid", "; ".join(validation.errors))
        document = copy.deepcopy(seed_document)
        return CandidateProfileStageResult(document, {}, _fingerprint(document), None, False, baseline_fingerprint)
    document = {section: [] for section in _DERIVED_COLLECTIONS}
    if not evidence_ids:
        return CandidateProfileStageResult(document, {}, _fingerprint(document), None, False, baseline_fingerprint)
    request = LlmTaskRequest(
        routing_part="candidate_profile_derived_claims",
        prompt=_render_task_prompt("candidate_profile_derived_claims", {"approved_baseline": baseline}),
        response_mode="json_schema",
        instructions="Return only evidence-backed derived claims. Never add baseline facts, evidence text, IDs, or source locations.",
        schema_name="candidate_profile_derived_claims",
        schema=_DERIVED_RESPONSE_SCHEMA,
    )
    result = _run_llm(
        request,
        lambda value: _validate_derived_payload(value, evidence_ids),
        llm_runner,
        document,
    )
    annotations: dict[str, Any] = {}
    for claim in result.parsed_value["claims"]:
        section = str(claim["section"])
        name = str(claim["name"]).strip()
        refs = list(dict.fromkeys(str(value) for value in claim["evidence_refs"]))
        identifier = _stable_id(_DERIVED_ID_PREFIX[section], [section, name.casefold(), refs])
        item = {
            "id": identifier,
            "name": name,
            "origin": str(claim.get("origin") or "llm_inferred"),
            "confidence": float(claim["confidence"]),
            "support_status": "supported",
            "evidence_refs": refs,
        }
        document[section].append(item)
        annotations[f"/{section}/{identifier}/name"] = _annotation(
            origin=item["origin"],
            source_block_ids=[],
            confidence=item["confidence"],
            regenerable=True,
        )
    return CandidateProfileStageResult(
        document=document,
        annotations=annotations,
        fingerprint=_fingerprint(document),
        runtime_evidence=project_llm_runtime_evidence(result),
        llm_called=True,
        baseline_fingerprint=baseline_fingerprint,
    )


def resolve_regeneration_targets(
    annotations: dict[str, Any],
    targets: list[str],
) -> tuple[str, ...]:
    if targets == ["*"]:
        resolved = tuple(path for path, value in annotations.items() if value.get("regenerable"))
        if not resolved:
            raise CandidateProfileServiceError("candidate_profile_field_not_regenerable", "No fields can be regenerated")
        return resolved
    if not targets:
        raise CandidateProfileServiceError("candidate_profile_field_not_regenerable", "Regeneration target is required")
    resolved: list[str] = []
    for target in targets:
        if not bool((annotations.get(target) or {}).get("regenerable")):
            raise CandidateProfileServiceError("candidate_profile_field_not_regenerable", f"Field cannot be regenerated: {target}")
        if target not in resolved:
            resolved.append(target)
    return tuple(resolved)


def _find_list_item(values: list[Any], item_id: str) -> dict[str, Any]:
    for value in values:
        if isinstance(value, dict) and str(value.get("id")) == item_id:
            return value
    raise CandidateProfileServiceError("candidate_profile_field_not_found", f"Field not found: {item_id}")


def _replace_path(document: dict[str, Any], path: str, value: Any) -> None:
    segments = [segment for segment in path.split("/") if segment]
    target: Any = document
    for segment in segments[:-1]:
        if isinstance(target, list):
            target = _find_list_item(target, segment)
        elif isinstance(target, dict) and segment in target:
            target = target[segment]
        else:
            raise CandidateProfileServiceError("candidate_profile_field_not_found", f"Field not found: {path}")
    final = segments[-1]
    if isinstance(target, list):
        target = _find_list_item(target, final)
        if not isinstance(value, dict):
            raise CandidateProfileServiceError("validation_failed", "Collection entry replacement requires a mapping")
        target.clear()
        target.update(copy.deepcopy(value))
    elif isinstance(target, dict) and final in target:
        target[final] = copy.deepcopy(value)
    else:
        raise CandidateProfileServiceError("candidate_profile_field_not_found", f"Field not found: {path}")


def regenerate_review(
    stage: str,
    document: dict[str, Any],
    annotations: dict[str, Any],
    targets: list[str],
    *,
    llm_runner: _LlmRunner | None = None,
) -> CandidateProfileStageResult:
    resolved = resolve_regeneration_targets(annotations, targets)
    working = copy.deepcopy(document)
    routing_part = "candidate_profile_base_mapping" if stage == "baseline" else "candidate_profile_derived_claims"
    response_schema = copy.deepcopy(_REGENERATION_RESPONSE_SCHEMA)
    response_schema["properties"]["proposals"]["items"] = {
        "type": "object",
        "properties": {"path": {"type": "string", "enum": list(resolved)}},
        "required": ["path"],
    }
    request = LlmTaskRequest(
        routing_part=routing_part,
        prompt=_render_task_prompt(routing_part, {"document": working, "targets": resolved, "mode": "regenerate"}),
        response_mode="json_schema",
        instructions=f"Return replacements only for requested canonical paths: {json.dumps(resolved)}.",
        schema_name=f"candidate_profile_{stage}_regeneration",
        schema=response_schema,
    )

    def validator(value: Any) -> LlmValidationResult:
        if not isinstance(value, dict) or not isinstance(value.get("proposals"), list):
            return _validation(["proposals must be a list"])
        paths = [proposal.get("path") for proposal in value["proposals"] if isinstance(proposal, dict)]
        return _validation([] if paths and set(paths) <= set(resolved) else ["regeneration returned an unrequested path"])

    result = _run_llm(request, validator, llm_runner, working)
    updated_annotations = copy.deepcopy(annotations)
    for proposal in result.parsed_value["proposals"]:
        _replace_path(working, str(proposal["path"]), proposal.get("value"))
        previous = updated_annotations[str(proposal["path"])]
        updated_annotations[str(proposal["path"])] = {
            **previous,
            "origin": "llm_normalized" if stage == "baseline" else "llm_inferred",
            "confidence": float(proposal.get("confidence", previous.get("confidence", 0.0))),
        }
    return CandidateProfileStageResult(
        working,
        updated_annotations,
        _fingerprint(working),
        project_llm_runtime_evidence(result),
        True,
    )


def _collect_ids(value: Any) -> list[str]:
    identifiers: list[str] = []
    if isinstance(value, dict):
        if value.get("id") is not None:
            identifiers.append(str(value["id"]))
        for child in value.values():
            identifiers.extend(_collect_ids(child))
    elif isinstance(value, list):
        for child in value:
            identifiers.extend(_collect_ids(child))
    return identifiers


def apply_review_operations(
    stage: str,
    document: dict[str, Any],
    operations: list[dict[str, Any]],
) -> dict[str, Any]:
    if stage not in {"baseline", "derived"}:
        raise CandidateProfileServiceError("candidate_profile_transition_invalid", "Unknown review stage")
    working = copy.deepcopy(document)
    for operation in operations:
        action = str(operation.get("operation") or "")
        path = str(operation.get("path") or "")
        if action == "replace":
            _replace_path(working, path, operation.get("value"))
        elif action == "add":
            segments = [segment for segment in path.split("/") if segment]
            target: Any = working
            for segment in segments:
                if isinstance(target, list):
                    target = _find_list_item(target, segment)
                elif isinstance(target, dict) and segment in target:
                    target = target[segment]
                else:
                    raise CandidateProfileServiceError("candidate_profile_field_not_found", f"Field not found: {path}")
            if not isinstance(target, list):
                raise CandidateProfileServiceError("validation_failed", "Add target must be a collection")
            target.append(copy.deepcopy(operation.get("value")))
        elif action == "remove":
            segments = [segment for segment in path.split("/") if segment]
            target: Any = working
            for segment in segments[:-1]:
                target = _find_list_item(target, segment) if isinstance(target, list) else target.get(segment)
                if target is None:
                    raise CandidateProfileServiceError("candidate_profile_field_not_found", f"Field not found: {path}")
            final = segments[-1]
            if isinstance(target, list):
                target.remove(_find_list_item(target, final))
            elif isinstance(target, dict) and final in target:
                target.pop(final)
            else:
                raise CandidateProfileServiceError("candidate_profile_field_not_found", f"Field not found: {path}")
        else:
            raise CandidateProfileServiceError("validation_failed", "Unsupported review operation")
    identifiers = _collect_ids(working)
    if len(identifiers) != len(set(identifiers)):
        raise CandidateProfileServiceError("validation_failed", "duplicate_id")
    return working


def invalidation_for_stage(stage: str) -> dict[str, bool]:
    if stage == "baseline":
        return {
            "approved_baseline": True,
            "derived_draft": True,
            "approved_derived": True,
            "confirmation": True,
        }
    if stage == "derived":
        return {"approved_derived": True, "confirmation": True}
    raise CandidateProfileServiceError("candidate_profile_transition_invalid", "Unknown review stage")


def approve_review(
    stage: str,
    document: dict[str, Any],
    *,
    expected_fingerprint: str | None,
    baseline_fingerprint: str | None = None,
) -> dict[str, Any]:
    fingerprint = _fingerprint(document)
    if expected_fingerprint is not None and expected_fingerprint != fingerprint:
        raise CandidateProfileServiceError("candidate_profile_fingerprint_conflict", "Review fingerprint changed")
    if stage not in {"baseline", "derived"}:
        raise CandidateProfileServiceError("candidate_profile_transition_invalid", "Unknown review stage")
    return {
        "stage": stage,
        "document": copy.deepcopy(document),
        "fingerprint": fingerprint,
        "baseline_fingerprint": baseline_fingerprint if stage == "derived" else None,
    }


def assemble_confirmation(
    profile_name: str,
    approved_baseline: dict[str, Any],
    approved_derived: dict[str, Any],
) -> dict[str, Any]:
    if approved_baseline.get("stage") != "baseline" or approved_derived.get("stage") != "derived":
        raise CandidateProfileServiceError("candidate_profile_transition_invalid", "Approved baseline and derived snapshots are required")
    if approved_derived.get("baseline_fingerprint") != approved_baseline.get("fingerprint"):
        raise CandidateProfileServiceError("candidate_profile_fingerprint_conflict", "Derived snapshot belongs to another baseline")
    canonical = {
        "schema_version": "candidate-profile.v2",
        **copy.deepcopy(approved_baseline["document"]),
        **copy.deepcopy(approved_derived["document"]),
    }
    errors = validate_candidate_profile_v2(canonical)
    if errors:
        raise CandidateProfileServiceError("validation_failed", "; ".join(errors))
    if not _evidence_ids(canonical):
        raise CandidateProfileServiceError("candidate_profile_no_evidence", "Candidate Profile has no runnable evidence")
    checksum = canonical_candidate_checksum(canonical)
    fingerprint = _fingerprint(
        {
            "profile_name": profile_name,
            "baseline": approved_baseline["fingerprint"],
            "derived": approved_derived["fingerprint"],
            "checksum": checksum,
        }
    )
    return {
        "profile_name": profile_name,
        "fingerprint": fingerprint,
        "approval_fingerprints": {
            "baseline": approved_baseline["fingerprint"],
            "derived": approved_derived["fingerprint"],
        },
        "profile": {
            "checksum": checksum,
            "schema_version": "candidate-profile.v2",
            "canonical": canonical,
        },
        "readiness": {"ready": True, "blocking_errors": []},
        "warnings": [],
    }


def retry_failed_stage(failure: dict[str, Any]) -> str:
    if not failure.get("retryable"):
        raise CandidateProfileServiceError("candidate_profile_transition_invalid", "Failure is not retryable")
    stage = str(failure.get("stage") or "")
    if stage in {"extraction", "base_mapping"}:
        return "extracting_base"
    if stage == "derived_claims":
        return "deriving"
    if stage == "confirmation":
        return "ready_to_confirm"
    raise CandidateProfileServiceError("candidate_profile_transition_invalid", "Failed stage cannot be resumed")


def _stage_result_payload(result: CandidateProfileStageResult) -> dict[str, Any]:
    return {
        "document": result.document,
        "annotations": result.annotations,
        "fingerprint": result.fingerprint,
        "runtime_evidence": result.runtime_evidence,
        "baseline_fingerprint": result.baseline_fingerprint,
    }


def execute_candidate_profile_stage(
    *,
    attempt_id: str,
    stage: str,
    claim_id: str,
    expected_revision: int,
    targets: list[str] | None = None,
    store: Any | None = None,
) -> dict[str, Any]:
    if stage not in {"base_mapping", "derived_claims"}:
        raise CandidateProfileServiceError(
            "candidate_profile_transition_invalid", "Unknown processing stage"
        )
    if store is None:
        from fitcv_cp.store import ControlPlaneStore

        store = ControlPlaneStore()
    try:
        if stage == "base_mapping":
            source = store.get_candidate_profile_source(attempt_id)
            if source is None:
                raise CandidateProfileServiceError(
                    "candidate_profile_source_not_found", "Candidate Profile source not found"
                )
            ingest = ingest_candidate_source(
                str(source["filename"]),
                str(source["media_type"]),
                bytes(source["content"]),
            )
            if targets:
                current = store.get_candidate_profile_review(attempt_id, "baseline")
                if current is None:
                    raise CandidateProfileServiceError(
                        "candidate_profile_transition_invalid", "Baseline draft is unavailable"
                    )
                result = regenerate_review(
                    "baseline", current["document"], current["annotations"], targets
                )
                source_blocks = None
            else:
                result = build_baseline_review(ingest)
                source_blocks = copy.deepcopy(list(ingest.source_blocks))
                scoped_ids = {
                    str(block["block_id"]): _stable_id("block", [attempt_id, block["block_id"]])
                    for block in source_blocks
                }
                for block in source_blocks:
                    block["block_id"] = scoped_ids[str(block["block_id"])]
                for annotation in result.annotations.values():
                    annotation["source_block_ids"] = [
                        scoped_ids.get(str(block_id), str(block_id))
                        for block_id in annotation.get("source_block_ids") or []
                    ]
            payload = _stage_result_payload(result)
            payload["extraction_fingerprint"] = ingest.extraction_fingerprint
            return store.publish_candidate_profile_stage_result(
                attempt_id,
                stage="baseline",
                claim_id=claim_id,
                expected_revision=expected_revision,
                result=payload,
                source_blocks=source_blocks,
            )

        attempt = store.get_candidate_profile_creation_attempt(attempt_id)
        baseline = store.get_candidate_profile_review(attempt_id, "baseline")
        if attempt is None or baseline is None:
            raise CandidateProfileServiceError(
                "candidate_profile_transition_invalid", "Approved baseline is unavailable"
            )
        approved_fingerprint = attempt["fingerprints"]["approved_baseline"]
        if baseline["fingerprint"] != approved_fingerprint:
            raise CandidateProfileServiceError(
                "candidate_profile_fingerprint_conflict", "Approved baseline changed"
            )
        if targets:
            current = store.get_candidate_profile_review(attempt_id, "derived")
            if current is None:
                raise CandidateProfileServiceError(
                    "candidate_profile_transition_invalid", "Derived draft is unavailable"
                )
            result = regenerate_review(
                "derived", current["document"], current["annotations"], targets
            )
            result = CandidateProfileStageResult(
                result.document,
                result.annotations,
                result.fingerprint,
                result.runtime_evidence,
                result.llm_called,
                baseline_fingerprint=str(approved_fingerprint),
            )
        else:
            source = store.get_candidate_profile_source(attempt_id)
            seed_document = None
            if source is not None:
                ingest = ingest_candidate_source(
                    str(source["filename"]),
                    str(source["media_type"]),
                    bytes(source["content"]),
                )
                seed_document = build_baseline_review(ingest).derived_seed
            result = build_derived_review(
                {
                    "stage": "baseline",
                    "document": baseline["document"],
                    "fingerprint": baseline["fingerprint"],
                },
                seed_document=seed_document,
            )
        return store.publish_candidate_profile_stage_result(
            attempt_id,
            stage="derived",
            claim_id=claim_id,
            expected_revision=expected_revision,
            result=_stage_result_payload(result),
        )
    except CandidateIngestError as exc:
        store.fail_candidate_profile_stage(
            attempt_id,
            claim_id=claim_id,
            expected_revision=expected_revision,
            code=exc.code,
            message=str(exc),
            retryable=False,
            stage=stage,
        )
        raise
    except CandidateProfileServiceError as exc:
        store.fail_candidate_profile_stage(
            attempt_id,
            claim_id=claim_id,
            expected_revision=expected_revision,
            code=exc.code,
            message=str(exc),
            retryable=exc.retryable,
            stage=stage,
        )
        raise
