"""Deterministic, read-only Bronze/Silver/Gold projections for FitCV evidence."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any, Iterable


ANALYTICS_SCHEMA_VERSION = "fitcv.analytics.v1"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def build_bronze_observations(
    sources: dict[str, Iterable[dict[str, Any]]],
    *,
    source_commit: str,
    declared_input_fingerprint: str,
    ingested_at: str,
) -> list[dict[str, Any]]:
    """Flatten source-owned observations without changing operational state."""
    rows: list[dict[str, Any]] = []
    for observation_type in sorted(sources):
        for item in sources[observation_type]:
            payload = dict(item)
            source_id = str(
                payload.get("source_id")
                or payload.get("id")
                or payload.get("run_job_id")
                or payload.get("run_id")
                or ""
            ).strip()
            observed_at = str(
                payload.get("observed_at")
                or payload.get("created_at")
                or payload.get("accepted_at")
                or ""
            )
            identity = {
                "observation_type": observation_type,
                "source_id": source_id,
                "payload": payload,
            }
            rows.append(
                {
                    "observation_id": _digest(identity),
                    "observation_type": observation_type,
                    "source_id": source_id,
                    "observed_at": observed_at,
                    "source_schema": str(payload.get("schema_version") or "unknown"),
                    "source_commit": source_commit,
                    "declared_input_fingerprint": declared_input_fingerprint,
                    "ingested_at": ingested_at,
                    "payload": payload,
                }
            )
    return sorted(rows, key=lambda row: (row["observation_type"], row["source_id"], row["observation_id"]))


def build_silver_facts(bronze: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate Bronze by observation identity and retain validity semantics."""
    facts: dict[str, dict[str, Any]] = {}
    for observation in bronze:
        row = dict(observation)
        observation_id = str(row.get("observation_id") or "").strip()
        payload = row.get("payload")
        if not observation_id or not isinstance(payload, dict):
            continue
        fact = {
            **row,
            "entity_id": f"{row.get('observation_type')}:{row.get('source_id')}",
            "validity": str(payload.get("validity") or "valid"),
        }
        existing = facts.get(observation_id)
        if existing is None or _json(fact) < _json(existing):
            facts[observation_id] = fact
    return sorted(facts.values(), key=lambda row: row["observation_id"])


def _known_sum(values: list[Any]) -> float | int | None:
    if not values or any(value is None for value in values):
        return None
    return sum(values)


def build_gold_cv_effort(silver: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate one-to-many work before joining accepted artifact identities."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in silver:
        payload = dict(fact.get("payload") or {})
        run_job_id = str(
            payload.get("run_job_id")
            or payload.get("job_id")
            or payload.get("source_id")
            or ""
        ).strip()
        if run_job_id:
            grouped[run_job_id].append({**fact, "payload": payload})

    result: list[dict[str, Any]] = []
    for run_job_id, facts in sorted(grouped.items()):
        artifacts = [
            fact for fact in facts
            if fact.get("observation_type") in {"artifact", "accepted_artifact"}
            and str(fact["payload"].get("status") or "") in {"accepted", "succeeded"}
            and bool(fact["payload"].get("accepted", True))
        ]
        artifact_keys = sorted({
            (
                run_job_id,
                str(fact["payload"].get("artifact_version_id") or fact["payload"].get("version_id") or ""),
            )
            for fact in artifacts
        })
        provider = [fact for fact in facts if fact.get("observation_type") == "provider_attempt"]
        generation = [fact for fact in facts if fact.get("observation_type") == "generation_attempt"]
        review = [fact for fact in facts if fact.get("observation_type") == "review_action"]
        provider_calls = _known_sum([fact["payload"].get("provider_call_count") for fact in provider])
        tokens = _known_sum([fact["payload"].get("token_total") for fact in provider])
        result.append(
            {
                "schema_version": ANALYTICS_SCHEMA_VERSION,
                "metric": "gold_cv_effort",
                "grain": "run_job_id + artifact_version_id",
                "run_job_id": run_job_id,
                "accepted_artifact_count": len([key for key in artifact_keys if key[1]]),
                "attempted_work_count": len({fact["observation_id"] for fact in facts}),
                "provider_attempt_count": len(provider),
                "generation_attempt_count": len(generation),
                "failed_generation_attempt_count": sum(
                    str(fact["payload"].get("status") or "") in {"failed", "generation_failed", "validation_failed"}
                    for fact in generation
                ),
                "review_action_count": len(review),
                "provider_call_count": provider_calls,
                "token_total": tokens,
                "per_accepted_artifact": (
                    {
                        "provider_call_count": provider_calls / len(artifact_keys),
                        "token_total": tokens / len(artifact_keys),
                    }
                    if artifact_keys and provider_calls is not None and tokens is not None
                    else None
                ),
                "unavailable_reason": None if artifact_keys else "accepted_artifact_count_zero",
                "source_observation_ids": sorted(fact["observation_id"] for fact in facts),
            }
        )
    return result


def build_gold_acceptance_state(
    registry: dict[str, Any],
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    records = list(registry.get("records") or [])
    output: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: str(item.get("evidence_id") or "")):
        output.append(
            {
                "schema_version": ANALYTICS_SCHEMA_VERSION,
                "metric": "gold_acceptance_state",
                "evidence_id": record.get("evidence_id"),
                "claim": record.get("claim"),
                "status": record.get("status"),
                "cohort_id": record.get("cohort_id"),
                "cohort_type": record.get("cohort_type"),
                "source_commit": record.get("source_commit"),
                "declared_input_fingerprint": record.get("declared_input_fingerprint"),
                "material_metrics_sha256": record.get("material_metrics_sha256"),
                "implementation": state.get("implementation"),
                "acceptance": state.get("acceptance"),
                "measurement": state.get("measurement"),
                "optimization": state.get("optimization_result"),
                "historical": record.get("status") in {"historical", "superseded"},
                "deferred": record.get("status") == "deferred",
            }
        )
    return output


def material_gold_digest(gold: dict[str, Any]) -> str:
    return _digest({key: value for key, value in gold.items() if key not in {"generated_at", "ingested_at"}})
