"""Frozen evaluation metrics for requirement-aware shortlist admission."""

from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from fitcv.shortlist_selection import select_requirement_aware_jobs

EVALUATION_SCHEMA_VERSION = "shortlist_evaluation_v1"
DEFAULT_EVIDENCE_CORRECTNESS_GATE = 0.95
DEFAULT_UNKNOWN_RATE_GATE = 0.10
DEFAULT_LATENCY_COST_MULTIPLIER_GATE = 2.0


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _identity(row: Mapping[str, Any]) -> str:
    return str(row.get("canonical_job_identity") or row.get("job_url") or "").strip()


def _percentile(values: Iterable[float], percentile: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    return ordered[max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))]


def _label_state(value: Any) -> str | None:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return {
        "supported": "S",
        "support": "S",
        "s": "S",
        "partial": "P",
        "qualifier_only": "P",
        "p": "P",
        "reviewed_no_support": "E",
        "no_support": "E",
        "unsupported": "E",
        "e": "E",
        "unresolved": "U",
        "assessment_failure": "U",
        "assessment_failed": "U",
        "retrieval_failure": "U",
        "retrieval_failed": "U",
        "unknown": "U",
        "u": "U",
    }.get(normalized)


def _occurrence_metrics(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    total = 0
    correct = 0
    contradiction_total = 0
    contradiction_correct = 0
    unknown = 0
    for row in rows:
        coverage = row.get("coverage") or row.get("coverage_summary") or {}
        for state in coverage.get("states") or []:
            if not isinstance(state, Mapping):
                continue
            expected = _label_state(
                state.get("oracle_state") or state.get("expected_state") or state.get("gold_state")
            )
            actual = _label_state(state.get("state") or state.get("coverage_state"))
            if actual == "U":
                unknown += 1
            if expected is None:
                continue
            total += 1
            correct += int(actual == expected)
            if "oracle_contradiction" in state or "expected_contradiction" in state:
                expected_contradiction = bool(
                    state.get("oracle_contradiction", state.get("expected_contradiction"))
                )
                actual_contradiction = bool(state.get("contradiction") or state.get("contradicted"))
                contradiction_total += 1
                contradiction_correct += int(actual_contradiction == expected_contradiction)
    assessed_total = total or unknown
    return {
        "labeled_occurrences": total,
        "correct_occurrences": correct,
        "evidence_correctness": (correct / total if total else None),
        "contradiction_labels": contradiction_total,
        "contradiction_accuracy": (
            contradiction_correct / contradiction_total if contradiction_total else None
        ),
        "unknown_occurrences": unknown,
        "unknown_rate": (unknown / assessed_total if assessed_total else None),
    }


def evaluate_shortlist_pool(
    fixture: Mapping[str, Any],
    *,
    profile_revision: str,
    as_of: str,
    split_id: str,
    requirement_contract_fingerprint: str,
    eligibility_policy_fingerprint: str,
    cache_condition: str,
    legacy_baseline: Mapping[str, Any] | None = None,
    latency_samples_ms: Iterable[float] = (),
    retrieval_cost: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    if cache_condition not in {"cold", "warm"}:
        raise ValueError("cache_condition must be 'cold' or 'warm'")
    jobs = [dict(row) for row in fixture.get("jobs") or [] if isinstance(row, Mapping)]
    capacity = int(fixture.get("admission_capacity") or 50)
    threshold = int(fixture.get("relevance_grade_threshold") or 0)
    started = time.perf_counter()
    selection = select_requirement_aware_jobs(jobs, capacity=capacity)
    observed_wall_clock_ms = (time.perf_counter() - started) * 1000
    replay = select_requirement_aware_jobs(list(reversed(jobs)), capacity=capacity)

    relevant = {_identity(row) for row in jobs if int(row.get("relevance_grade") or 0) >= threshold}
    aware_admitted = {_identity(row) for row in selection["admitted"]}
    legacy_pool = [row for row in jobs if not bool(row.get("legacy_excluded"))]
    legacy_admitted = {_identity(row) for row in legacy_pool[:capacity]}
    occurrence = _occurrence_metrics(jobs)
    latency_samples = list(latency_samples_ms)
    metrics = {
        "recall_at_50": len(relevant & aware_admitted) / len(relevant) if relevant else None,
        "legacy_recall_at_50": len(relevant & legacy_admitted) / len(relevant) if relevant else None,
        "legacy_relevant_count": len(relevant & legacy_admitted),
        "aware_relevant_count": len(relevant & aware_admitted),
        "relevant_count": len(relevant),
        "disagreement_count": sum(
            (_identity(row) in aware_admitted) != (_identity(row) in legacy_admitted) for row in jobs
        ),
        "determinism": int(
            selection["decision_fingerprint"] == replay["decision_fingerprint"]
            and selection["assessment_fingerprint"] == replay["assessment_fingerprint"]
        ),
        "observed_wall_clock_ms": round(observed_wall_clock_ms, 3),
        "p95_latency_ms": _percentile(latency_samples, 0.95),
        **occurrence,
    }
    if retrieval_cost:
        metrics["retrieval_cost"] = dict(retrieval_cost)

    baseline = dict(legacy_baseline or {})
    gates = {
        "evidence_correctness": (
            metrics["evidence_correctness"] is not None
            and metrics["evidence_correctness"] >= DEFAULT_EVIDENCE_CORRECTNESS_GATE
        ),
        "unknown_rate": (
            metrics["unknown_rate"] is not None and metrics["unknown_rate"] <= DEFAULT_UNKNOWN_RATE_GATE
        ),
        "determinism": metrics["determinism"] == 1,
        "recall_at_50": (
            metrics["recall_at_50"] is not None
            and baseline.get("recall_at_50") is not None
            and metrics["recall_at_50"] >= float(baseline["recall_at_50"])
        ),
        "latency": (
            metrics["p95_latency_ms"] is not None
            and baseline.get("p95_latency_ms") is not None
            and metrics["p95_latency_ms"] <= DEFAULT_LATENCY_COST_MULTIPLIER_GATE * float(baseline["p95_latency_ms"])
        ),
        "cost": (
            retrieval_cost is not None
            and baseline.get("retrieval_cost") is not None
            and float(retrieval_cost.get("total", 0))
            <= DEFAULT_LATENCY_COST_MULTIPLIER_GATE * float(dict(baseline["retrieval_cost"]).get("total", 0))
        ),
    }
    blocked_reasons = [name for name, passed in gates.items() if not passed]
    metadata = {
        "profile_revision": profile_revision,
        "as_of": as_of,
        "split_id": split_id,
        "cache_condition": cache_condition,
        "requirement_contract_fingerprint": requirement_contract_fingerprint,
        "eligibility_policy_fingerprint": eligibility_policy_fingerprint,
        "input_snapshot_fingerprint": _stable_hash(
            {
                "jobs": jobs,
                "admission_capacity": capacity,
                "relevance_grade_threshold": threshold,
            }
        ),
    }
    artifact = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "fixture_role": fixture.get("fixture_role"),
        "metrics": metrics,
        "gates": gates,
        "promotion_eligible": not blocked_reasons,
        "blocked_reasons": blocked_reasons,
        "baseline": baseline,
        "metadata": metadata,
        "selection": {
            "strategy": selection["strategy"],
            "admission_capacity": capacity,
            "evaluation_pool_id": selection["evaluation_pool_id"],
            "decision_fingerprint": selection["decision_fingerprint"],
            "assessment_fingerprint": selection["assessment_fingerprint"],
        },
    }
    artifact["artifact_fingerprint"] = _stable_hash(artifact)
    return artifact


def evaluation_as_of_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
