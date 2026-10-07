"""@meta
name: reuse_law_engine
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.exact-match-late-stage-reuse
responsibility:
  - Provide reusable policy-gate helpers for cross-stage reuse decisions.
inputs:
  - Stage semantic/runtime fingerprints and policy gate inputs
outputs:
  - Deterministic reuse identities, decisions, and provenance payloads
lifecycle:
  - status: active
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


def _sha256_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ReuseIdentity:
    stage: str
    scope_tier: str
    proposal_semantic_id: str
    runtime_invariance_id: str
    stage_input_fingerprint: str
    candidate_revision_fingerprint: str | None
    source_fingerprint: str | None
    final_reuse_key: str


@dataclass(frozen=True)
class ReuseDecision:
    enabled: bool
    seed_available: bool
    runtime_match: bool
    semantic_match: bool
    soft_blocked: bool
    scope_tier: str
    seed_run_id: str | None
    seed_created_at: str | None
    identity_match: bool
    artifact_match: bool
    invalidated_units: tuple[str, ...]
    stage: str
    reuse_key: str


def build_identity(
    stage: str,
    semantic_payload: dict[str, Any] | None,
    runtime_payload: dict[str, Any] | None,
    scope_tier: str = "dataset",
    *,
    stage_input_fingerprint: str | None = None,
    candidate_revision_fingerprint: str | None = None,
    source_fingerprint: str | None = None,
) -> ReuseIdentity:
    stage_name = str(stage or "").strip()
    if not stage_name:
        raise ValueError("reuse_identity_stage_required")
    semantic = dict(semantic_payload or {})
    runtime = dict(runtime_payload or {})
    scope = str(scope_tier or "dataset").strip().lower() or "dataset"
    if scope not in {"strict", "dataset", "global"}:
        scope = "dataset"
    semantic_fields = {
        "field": str(semantic.get("field") or ""),
        "alias": str(semantic.get("alias") or ""),
        "canonical": str(semantic.get("canonical") or ""),
        "sorted_candidates": [str(x) for x in list(semantic.get("sorted_candidates") or [])],
        "family": str(semantic.get("family") or ""),
    }
    runtime_fields = {
        "provider": str(runtime.get("provider") or ""),
        "model": str(runtime.get("model") or ""),
        "prompt_version": str(runtime.get("prompt_version") or ""),
        "triage_version": str(runtime.get("triage_version") or ""),
        "semantic_settings_hash": str(runtime.get("semantic_settings_hash") or ""),
        "guardrail_flags": [str(x) for x in list(runtime.get("guardrail_flags") or [])],
    }
    if not any(semantic_fields.values()) and not any(runtime_fields.values()):
        raise ValueError("reuse_identity_inputs_required")
    proposal_semantic_id = _sha256_json(semantic_fields)
    runtime_invariance_id = _sha256_json(runtime_fields)
    candidate_revision = str(
        candidate_revision_fingerprint
        or semantic.get("candidate_revision")
        or semantic.get("candidate_profile_revision")
        or runtime.get("candidate_revision")
        or ""
    ).strip() or None
    source = str(
        source_fingerprint
        or semantic.get("source_fingerprint")
        or semantic.get("raw_job_fingerprint")
        or runtime.get("source_fingerprint")
        or ""
    ).strip() or None
    stage_input = str(stage_input_fingerprint or "").strip() or _sha256_json(
        {
            "semantic": semantic_fields,
            "runtime": runtime_fields,
            "source_fingerprint": source,
            "candidate_revision_fingerprint": candidate_revision,
        }
    )
    final_reuse_key = _sha256_json(
        {
            "proposal_semantic_id": proposal_semantic_id,
            "runtime_invariance_id": runtime_invariance_id,
            "stage_input_fingerprint": stage_input,
            "candidate_revision_fingerprint": candidate_revision,
            "source_fingerprint": source,
            "scope_tier_salt": scope,
            "stage": stage_name,
        }
    )
    return ReuseIdentity(
        stage=stage_name,
        scope_tier=scope,
        proposal_semantic_id=proposal_semantic_id,
        runtime_invariance_id=runtime_invariance_id,
        stage_input_fingerprint=stage_input,
        candidate_revision_fingerprint=candidate_revision,
        source_fingerprint=source,
        final_reuse_key=final_reuse_key,
    )


def evaluate_gate(
    identity: ReuseIdentity,
    gate_inputs: dict[str, Any] | None,
    policy: dict[str, Any] | None,
) -> ReuseDecision:
    inputs = dict(gate_inputs or {})
    cfg = dict(policy or {})
    return ReuseDecision(
        enabled=bool(cfg.get("enabled", True)),
        seed_available=bool(inputs.get("seed_available", False)),
        runtime_match=bool(inputs.get("runtime_match", False)),
        semantic_match=bool(inputs.get("semantic_match", False)),
        soft_blocked=bool(inputs.get("soft_blocked", False)),
        scope_tier=str(identity.scope_tier or "dataset"),
        seed_run_id=str(inputs.get("seed_run_id") or "") or None,
        seed_created_at=str(inputs.get("seed_created_at") or "") or None,
        identity_match=bool(inputs.get("identity_match", True)),
        artifact_match=bool(inputs.get("artifact_match", True)),
        invalidated_units=tuple(
            str(unit).strip()
            for unit in list(inputs.get("invalidated_units") or [])
            if str(unit).strip()
        ),
        stage=identity.stage,
        reuse_key=identity.final_reuse_key,
    )


def emit_provenance(decision: ReuseDecision) -> dict[str, Any]:
    if not decision.enabled:
        return _fresh("reuse_disabled", decision)
    if not decision.seed_available:
        return _fresh("seed_missing", decision)
    if not decision.runtime_match:
        return _fresh("runtime_mismatch", decision)
    if not decision.semantic_match:
        return _fresh("semantic_mismatch", decision)
    if decision.soft_blocked:
        return _fresh("soft_blocked", decision)
    if not decision.identity_match:
        return _fresh("identity_mismatch", decision)
    if not decision.artifact_match:
        return _fresh("artifact_mismatch", decision)
    return {
        "reuse_status": "reused_exact_match",
        "reuse_reason": "reuse_enabled",
        "scope_tier": decision.scope_tier,
        "decision_source": "policy_gate",
        "gate_runtime_match": decision.runtime_match,
        "gate_semantic_match": decision.semantic_match,
        "gate_soft_blocked": decision.soft_blocked,
        "seed_run_id": decision.seed_run_id,
        "seed_created_at": decision.seed_created_at,
        "invalidation_reason": None,
        "provenance_event": "hit",
        "stage": decision.stage,
        "reuse_key": decision.reuse_key,
        "invalidated_units": list(decision.invalidated_units),
    }


def _fresh(reason: str, decision: ReuseDecision) -> dict[str, Any]:
    return {
        "reuse_status": "fresh_compute",
        "reuse_reason": reason,
        "scope_tier": decision.scope_tier,
        "decision_source": "policy_gate",
        "gate_runtime_match": decision.runtime_match,
        "gate_semantic_match": decision.semantic_match,
        "gate_soft_blocked": decision.soft_blocked,
        "seed_run_id": decision.seed_run_id,
        "seed_created_at": decision.seed_created_at,
        "invalidation_reason": reason,
        "provenance_event": (
            "invalidation"
            if reason in {"identity_mismatch", "artifact_mismatch", "runtime_mismatch", "semantic_mismatch"}
            else "rejection"
        ),
        "stage": decision.stage,
        "reuse_key": decision.reuse_key,
        "invalidated_units": list(decision.invalidated_units),
    }
