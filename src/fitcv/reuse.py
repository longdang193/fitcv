"""@meta
name: reuse
type: module
domain: pipeline
ownership: infrastructure
responsibility:
  - Centralize cross-stage reuse policy normalization and decision-envelope helpers.
inputs:
  - Runtime config reuse block
outputs:
  - Normalized stage policy objects and deterministic reuse decision envelopes
lifecycle:
  - status: active
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fitcv.reuse_law_engine import build_identity, emit_provenance, evaluate_gate

_EXACT = "exact"
_EXACT_OR_CORE = "exact_or_core"
_SUCCEEDED_ONLY = "succeeded_only"
_SUCCEEDED_OR_CHECKPOINTED = "succeeded_or_checkpointed"

_STAGE_DEFAULTS: dict[str, dict[str, str]] = {
    "enrich": {"source_scope": _SUCCEEDED_OR_CHECKPOINTED, "match_mode": _EXACT},
    "ranking": {"source_scope": _SUCCEEDED_OR_CHECKPOINTED, "match_mode": _EXACT},
    "cv_analysis": {"source_scope": _SUCCEEDED_OR_CHECKPOINTED, "match_mode": _EXACT},
    "cv_generation": {"source_scope": _SUCCEEDED_OR_CHECKPOINTED, "match_mode": _EXACT},
    "synonym_triage": {"source_scope": _SUCCEEDED_OR_CHECKPOINTED, "match_mode": _EXACT_OR_CORE},
}

_STAGE_INVALIDATION_ORDER = (
    "enrich",
    "ranking",
    "cv_analysis",
    "cv_generation",
    "render",
)


@dataclass(frozen=True)
class ReuseStagePolicy:
    stage: str
    enabled: bool
    source_scope: str
    match_mode: str


def affected_reuse_units(stage: str, *, changed: bool = True) -> list[str]:
    """Return bounded downstream units invalidated by a stage change."""
    if not changed:
        return []
    stage_key = str(stage or "").strip().lower()
    if stage_key not in _STAGE_INVALIDATION_ORDER:
        return [stage_key] if stage_key else []
    start = _STAGE_INVALIDATION_ORDER.index(stage_key)
    return list(_STAGE_INVALIDATION_ORDER[start:])


def _normalize_source_scope(value: Any, *, fallback: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {_SUCCEEDED_ONLY, _SUCCEEDED_OR_CHECKPOINTED}:
        return normalized
    return fallback


def _normalize_match_mode(value: Any, *, fallback: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {_EXACT, _EXACT_OR_CORE}:
        return normalized
    return fallback


def resolve_reuse_stage_policy(config: dict[str, Any], stage: str) -> ReuseStagePolicy:
    stage_key = str(stage or "").strip()
    stage_defaults = dict(_STAGE_DEFAULTS.get(stage_key) or {})
    fallback_source_scope = str(stage_defaults.get("source_scope") or _SUCCEEDED_OR_CHECKPOINTED)
    fallback_match_mode = str(stage_defaults.get("match_mode") or _EXACT)

    reuse_block = dict(config.get("reuse") or {})
    stage_block = dict(reuse_block.get(stage_key) or {})

    return ReuseStagePolicy(
        stage=stage_key,
        enabled=bool(stage_block.get("enabled", True)),
        source_scope=_normalize_source_scope(stage_block.get("source_scope"), fallback=fallback_source_scope),
        match_mode=_normalize_match_mode(stage_block.get("match_mode"), fallback=fallback_match_mode),
    )


def build_reuse_decision(
    *,
    decision: str,
    reason_code: str,
    fingerprint: str | None,
    source_run_id: str | None = None,
    source_artifact_type: str | None = None,
    stage: str | None = None,
    provenance_event: str | None = None,
    invalidation_scope: str | None = None,
    affected_units: list[str] | None = None,
    reuse_key: str | None = None,
) -> dict[str, Any]:
    resolved_stage = str(stage or source_artifact_type or "").strip() or None
    resolved_decision = str(decision or "").strip()
    resolved_reason = str(reason_code or "").strip()
    if provenance_event:
        resolved_event = str(provenance_event).strip()
    elif resolved_decision in {"reused_exact_match", "reused"}:
        resolved_event = "hit"
    elif any(token in resolved_reason for token in ("mismatch", "stale", "changed", "invalidat")):
        resolved_event = "invalidation"
    else:
        resolved_event = "rejection"
    resolved_affected_units = [
        str(unit).strip()
        for unit in list(affected_units or [])
        if str(unit).strip()
    ]
    if not resolved_affected_units and resolved_event == "invalidation":
        resolved_affected_units = affected_reuse_units(resolved_stage or "")
    law_provenance: dict[str, Any] = {}
    if resolved_stage and fingerprint:
        try:
            identity = build_identity(
                resolved_stage,
                {"field": resolved_stage, "canonical": fingerprint},
                {"semantic_settings_hash": fingerprint},
                stage_input_fingerprint=fingerprint,
                source_fingerprint=fingerprint,
            )
            law_provenance = emit_provenance(
                evaluate_gate(
                    identity,
                    {
                        "seed_available": resolved_decision in {"reused", "reused_exact_match"},
                        "runtime_match": resolved_reason != "runtime_mismatch",
                        "semantic_match": resolved_reason != "semantic_mismatch",
                        "identity_match": resolved_decision in {"reused", "reused_exact_match"},
                        "artifact_match": resolved_decision in {"reused", "reused_exact_match"},
                        "invalidated_units": resolved_affected_units,
                    },
                    {"enabled": resolved_decision != "reuse_disabled"},
                )
            )
        except ValueError:
            law_provenance = {}
    return {
        "decision": resolved_decision,
        "reason_code": resolved_reason,
        "fingerprint": str(fingerprint or "").strip() or None,
        "source_run_id": str(source_run_id or "").strip() or None,
        "source_artifact_type": str(source_artifact_type or "").strip() or None,
        "stage": resolved_stage,
        "provenance_event": resolved_event,
        "invalidation_scope": (
            str(invalidation_scope or "").strip()
            or ("stage_and_downstream" if resolved_event == "invalidation" else None)
        ),
        "affected_units": resolved_affected_units,
        "reuse_key": str(reuse_key or law_provenance.get("reuse_key") or fingerprint or "").strip() or None,
        "identity_source": "reuse_law_engine" if law_provenance else None,
    }
