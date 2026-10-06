"""Deterministic, read-only Bronze/Silver/Gold projections for FitCV evidence."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import yaml


ANALYTICS_SCHEMA_VERSION = "fitcv.analytics.v2"
RECONCILABLE_OBSERVATION_TYPES = {
    "provider_attempt",
    "generation_attempt",
    "review_action",
    "artifact",
    "accepted_artifact",
}
TRACE_OBSERVATION_TYPES = {"trace", "generation_trace", "normalized_trace"}
RUN_JOB_OBSERVATION_TYPES = RECONCILABLE_OBSERVATION_TYPES
REQUIREMENT_DEMAND_OBSERVATION_TYPES = {"posting_requirement"}
POSTING_INVENTORY_OBSERVATION_TYPES = {"posting_inventory"}
CANDIDATE_GAP_OBSERVATION_TYPES = {"candidate_gap"}
INCOMPLETE_COVERAGE_VALUES = {"incomplete", "unavailable", "unknown", "invalid"}
DEFAULT_METRIC_REGISTRY = Path(__file__).resolve().parents[1] / "config/analytics_metrics.yaml"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def load_metric_registry(path: Path = DEFAULT_METRIC_REGISTRY) -> dict[str, Any]:
    registry = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if registry.get("schema_version") != "fitcv.analytics_metrics.v1":
        raise ValueError("analytics_metric_registry_schema_invalid")
    metrics = registry.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise ValueError("analytics_metric_registry_metrics_invalid")
    metric_ids: set[str] = set()
    required = {
        "metric_id", "version", "source_model", "grain", "numerator",
        "denominator", "dimensions", "cohort_policy", "null_policy",
        "coverage_metric", "owner", "description",
    }
    for metric in metrics:
        if not isinstance(metric, dict) or not required <= set(metric):
            raise ValueError("analytics_metric_definition_invalid")
        metric_id = str(metric["metric_id"])
        if not metric_id or metric_id in metric_ids:
            raise ValueError("analytics_metric_id_not_unique")
        metric_ids.add(metric_id)
    mapping = registry.get("claim_priority_map")
    if not isinstance(mapping, dict) or any(not isinstance(value, list) or not value for value in mapping.values()):
        raise ValueError("analytics_claim_priority_map_invalid")
    semantic_fields = registry.get("semantic_output_fields")
    if semantic_fields is not None and (not isinstance(semantic_fields, list) or not semantic_fields):
        raise ValueError("analytics_semantic_output_fields_invalid")
    if semantic_fields is not None and any(
        not {"numerator_field", "denominator_field", "dimension_fields"} <= set(metric)
        for metric in metrics
    ):
        raise ValueError("analytics_metric_semantic_definition_invalid")
    return registry


def compute_projection_input_fingerprint(
    repo_root: Path,
    registry_path: Path = DEFAULT_METRIC_REGISTRY,
) -> str:
    registry = load_metric_registry(registry_path)
    paths = registry.get("projection_inputs")
    if not isinstance(paths, list) or not paths:
        raise ValueError("analytics_projection_inputs_invalid")
    digest = hashlib.sha256()
    for relative in sorted({str(value).replace("\\", "/") for value in paths}):
        path = repo_root / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _logical_entity_id(observation_type: str, payload: dict[str, Any], source_id: str) -> str:
    fields = (
        "provider_attempt_id", "generation_attempt_id", "review_action_id",
        "artifact_id", "artifact_version_id", "version_id", "source_id", "id",
    )
    for field in fields:
        value = str(payload.get(field) or "").strip()
        if value:
            return f"{observation_type}:{value}"
    return f"{observation_type}:unresolved:{source_id}" if source_id else ""


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
            logical_entity_id = _logical_entity_id(observation_type, payload, source_id)
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
                    "logical_entity_id": logical_entity_id,
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
    """Reconcile mutable facts while preserving conflicting trace identities."""
    observations: dict[str, dict[str, Any]] = {}
    for observation in bronze:
        row = dict(observation)
        observation_id = str(row.get("observation_id") or "").strip()
        payload = row.get("payload")
        if not observation_id or not isinstance(payload, dict):
            continue
        fact = {
            **row,
            "entity_id": str(row.get("logical_entity_id") or ""),
            "validity": str(payload.get("validity") or "valid"),
        }
        existing = observations.get(observation_id)
        if existing is None or _json(fact) < _json(existing):
            observations[observation_id] = fact

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in observations.values():
        observation_type = str(fact.get("observation_type") or "")
        if observation_type in TRACE_OBSERVATION_TYPES or not fact.get("logical_entity_id"):
            grouped[f"observation:{fact['observation_id']}"].append(fact)
        else:
            grouped[f"entity:{fact['logical_entity_id']}"] .append(fact)

    facts: list[dict[str, Any]] = []
    for key, candidates in sorted(grouped.items()):
        if key.startswith("observation:") or len(candidates) == 1:
            winner = candidates[0]
            winner["observation_history_ids"] = [winner["observation_id"]]
            winner["superseded_observation_ids"] = []
            facts.append(winner)
            continue
        def authority_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
            payload = dict(row.get("payload") or {})
            revision = payload.get("revision")
            if revision is None:
                revision = payload.get("source_revision")
            try:
                revision_key = f"1:{int(revision):030d}"
            except (TypeError, ValueError):
                revision_key = f"0:{str(revision or '')}"
            return (
                revision_key,
                str(row.get("observed_at") or ""),
                str(row.get("source_commit") or ""),
                str(row.get("observation_id") or ""),
                str(row.get("validity") or ""),
            )

        winner = max(candidates, key=authority_key)
        history = sorted(str(row["observation_id"]) for row in candidates)
        winner["observation_history_ids"] = history
        winner["superseded_observation_ids"] = [item for item in history if item != winner["observation_id"]]
        facts.append(winner)
    return sorted(facts, key=lambda row: (str(row.get("entity_id") or ""), row["observation_id"]))


def _known_sum(values: list[Any]) -> float | int | None:
    if not values or any(value is None for value in values):
        return None
    parsed: list[float] = []
    for value in values:
        if isinstance(value, bool):
            return None
        try:
            numeric = float(value)
        except (OverflowError, TypeError, ValueError):
            return None
        if numeric < 0 or not math.isfinite(numeric) or not numeric.is_integer():
            return None
        parsed.append(numeric)
    total = sum(parsed)
    if not math.isfinite(total):
        return None
    return int(total) if total.is_integer() else total


def _attempt_count(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        try:
            if value >= 1 and math.isfinite(float(value)):
                return value
        except OverflowError:
            return None
        return None
    try:
        numeric = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric < 1 or not numeric.is_integer():
        return None
    return int(numeric)


def _coverage_issue(fact: dict[str, Any]) -> str | None:
    if fact.get("validity") != "valid":
        return "invalid_source_fact"
    payload = dict(fact.get("payload") or {})
    for field in ("coverage", "coverage_status", "extraction_status", "evaluation_status"):
        value = str(payload.get(field) or "").strip().lower()
        if value in INCOMPLETE_COVERAGE_VALUES:
            return f"{field}_incomplete"
    return None


def _eligibility(payload: dict[str, Any]) -> bool | None:
    if "eligible" not in payload:
        return True
    value = payload.get("eligible")
    return value if isinstance(value, bool) else None


def _group_run_jobs(silver: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in silver:
        if fact.get("observation_type") not in RUN_JOB_OBSERVATION_TYPES:
            continue
        payload = dict(fact.get("payload") or {})
        run_job_id = str(
            payload.get("run_job_id")
            or payload.get("job_id")
            or payload.get("source_id")
            or ""
        ).strip()
        if run_job_id:
            grouped[run_job_id].append({**fact, "payload": payload})
    return grouped


def _artifact_identity(fact: dict[str, Any]) -> str:
    payload = dict(fact.get("payload") or {})
    for field in ("artifact_id", "artifact_version_id", "version_id"):
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None:
            return ""
    return ""


def _accepted_artifact_claim_valid(fact: dict[str, Any]) -> bool:
    payload = dict(fact.get("payload") or {})
    status = payload.get("status")
    accepted = payload.get("accepted", True)
    return (
        isinstance(status, str)
        and status.strip().lower() in {"accepted", "succeeded"}
        and isinstance(accepted, bool)
        and accepted
        and bool(_artifact_identity(fact))
    )


def _accepted_artifacts(facts: Iterable[dict[str, Any]], run_job_id: str) -> list[dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for fact in facts:
        if fact.get("validity") != "valid":
            continue
        payload = dict(fact.get("payload") or {})
        if fact.get("observation_type") not in {"artifact", "accepted_artifact"}:
            continue
        if not _accepted_artifact_claim_valid(fact):
            continue
        artifact_id = _artifact_identity(fact)
        if not artifact_id:
            continue
        row = artifacts.setdefault(
            artifact_id,
            {
                "schema_version": ANALYTICS_SCHEMA_VERSION,
                "metric": "gold_cv_artifact",
                "grain": "accepted_artifact",
                "run_job_id": run_job_id,
                "artifact_id": artifact_id,
                "accepted_at": payload.get("accepted_at"),
                "source_observation_ids": [],
                "render_proof": False,
                "verified_one_page": False,
            },
        )
        raw_render = payload.get("render_acceptance")
        render = raw_render if isinstance(raw_render, dict) else {}
        page_fit_status = str(payload.get("page_fit_status") or render.get("page_fit_status") or "").strip().lower()
        page_count = render.get("page_count")
        render_proof = (
            str(render.get("render_status") or "").strip().lower() == "pass"
            and isinstance(page_count, int)
            and not isinstance(page_count, bool)
            and page_count == 1
            and page_fit_status == "pass"
            and all(
                bool(re.fullmatch(r"[0-9a-f]{64}", str(render.get(field) or "")))
                for field in ("artifact_checksum", "content_sha256", "template_sha256", "render_config_fingerprint")
            )
            and bool(str(render.get("renderer_contract_version") or "").strip())
        )
        row["render_proof"] = row["render_proof"] or render_proof
        row["verified_one_page"] = row["verified_one_page"] or (
            render_proof and page_count == 1 and page_fit_status == "pass"
        )
        row["source_observation_ids"].append(fact["observation_id"])
    for row in artifacts.values():
        row["source_observation_ids"] = sorted(set(row["source_observation_ids"]))
    return [artifacts[key] for key in sorted(artifacts)]


def _accepted_artifact_facts(facts: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for fact in facts:
        observation_type = fact.get("observation_type")
        payload = dict(fact.get("payload") or {})
        status = str(payload.get("status") or "").strip().lower()
        if observation_type == "accepted_artifact" or (
            observation_type == "artifact"
            and (status in {"accepted", "succeeded"} or "accepted" in payload)
        ):
            result.append(fact)
    return result


def build_gold_cv_artifact(silver: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build one row per accepted artifact identity."""
    result: list[dict[str, Any]] = []
    for run_job_id, facts in sorted(_group_run_jobs(silver).items()):
        result.extend(_accepted_artifacts(facts, run_job_id))
    return result


def build_gold_run_job_effort(silver: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build one row per attempted run-job, including failed work."""
    grouped = _group_run_jobs(silver)

    result: list[dict[str, Any]] = []
    for run_job_id, facts in sorted(grouped.items()):
        artifacts = _accepted_artifacts(facts, run_job_id)
        accepted_artifact_facts = _accepted_artifact_facts(facts)
        accepted_artifact_coverage_complete = bool(accepted_artifact_facts) and all(
            fact.get("validity") == "valid"
            and _coverage_issue(fact) is None
            and bool(_artifact_identity(fact))
            and _accepted_artifact_claim_valid(fact)
            for fact in accepted_artifact_facts
        )
        invalid_facts = [fact for fact in facts if _coverage_issue(fact)]
        valid_facts = [fact for fact in facts if fact.get("validity") == "valid"]
        provider_all = [fact for fact in facts if fact.get("observation_type") == "provider_attempt"]
        generation_all = [fact for fact in facts if fact.get("observation_type") == "generation_attempt"]
        provider = [fact for fact in valid_facts if fact.get("observation_type") == "provider_attempt"]
        generation = [fact for fact in valid_facts if fact.get("observation_type") == "generation_attempt"]
        review_all = [fact for fact in facts if fact.get("observation_type") == "review_action"]
        review = [fact for fact in valid_facts if fact.get("observation_type") == "review_action"]
        provider_calls = _known_sum([fact["payload"].get("provider_call_count") for fact in provider_all])
        tokens = _known_sum([fact["payload"].get("token_total") for fact in provider_all])
        provider_facts_complete = bool(provider_all) and len(provider) == len(provider_all) and all(_coverage_issue(fact) is None for fact in provider_all)
        provider_call_coverage_complete = provider_facts_complete and provider_calls is not None
        token_coverage_complete = provider_facts_complete and tokens is not None
        generation_coverage_complete = not generation_all or (len(generation) == len(generation_all) and all(
            str(fact["payload"].get("status") or "").strip().lower() in {
                "accepted", "succeeded", "success", "failed", "generation_failed", "validation_failed", "persistence_failed"
            }
            and _attempt_count(fact["payload"].get("attempt_count")) is not None
            and _coverage_issue(fact) is None
            for fact in generation_all
        ))
        if not provider_call_coverage_complete:
            provider_calls = None
        if not token_coverage_complete:
            tokens = None
        generation_invalid = any(_coverage_issue(fact) is not None for fact in generation_all)
        eligibility_values = [_eligibility(dict(fact["payload"])) for fact in generation_all]
        eligible = (
            None if any(value is None for value in eligibility_values)
            else not any(value is False for value in eligibility_values)
        )
        eligible_attempt_coverage = (
            "unavailable"
            if generation_invalid or not generation_coverage_complete or any(value is None for value in eligibility_values)
            else "complete"
        )
        result.append(
            {
                "schema_version": ANALYTICS_SCHEMA_VERSION,
                "metric": "gold_run_job_effort",
                "grain": "run_job",
                "run_job_id": run_job_id,
                "cohort_id": next((fact["payload"].get("cohort_id") for fact in facts if fact["payload"].get("cohort_id")), "unclassified"),
                "cohort_type": next((fact["payload"].get("cohort_type") for fact in facts if fact["payload"].get("cohort_type")), "unclassified"),
                "eligible": eligible,
                "accepted_artifact_ids": [artifact["artifact_id"] for artifact in artifacts],
                "accepted_artifact_count": len(artifacts),
                "accepted_artifact_observation_count": len(accepted_artifact_facts),
                "accepted_artifact_coverage": "complete" if accepted_artifact_coverage_complete else "unavailable",
                "first_pass_success_count": int(
                    len(generation) == 1
                    and generation_coverage_complete
                    and str(generation[0]["payload"].get("status") or "").lower() in {"accepted", "succeeded", "success"}
                    and _attempt_count(generation[0]["payload"].get("attempt_count")) == 1
                    and bool(artifacts)
                ),
                "generation_attempt_coverage": "complete" if generation_coverage_complete else "unavailable",
                "eligible_attempt_coverage": eligible_attempt_coverage,
                "generation_observation_count": len(generation_all),
                "verified_one_page_count": sum(bool(artifact.get("verified_one_page")) for artifact in artifacts),
                "render_proof_count": sum(bool(artifact.get("render_proof")) for artifact in artifacts),
                "render_proof_coverage": "complete" if artifacts and all(bool(artifact.get("render_proof")) for artifact in artifacts) else "unavailable",
                "attempted_work_count": len({fact["observation_id"] for fact in valid_facts}),
                "manual_attempted_run_job_count": 1,
                "review_action_coverage": "complete" if review_all and len(review) == len(review_all) and all(_coverage_issue(fact) is None for fact in review_all) else "unavailable",
                "provider_attempt_count": len(provider),
                "provider_call_coverage": "complete" if provider_call_coverage_complete else "unavailable",
                "token_coverage": "complete" if token_coverage_complete else "unavailable",
                "generation_attempt_count": len(generation),
                "failed_generation_attempt_count": sum(
                    str(fact["payload"].get("status") or "") in {"failed", "generation_failed", "validation_failed", "persistence_failed"}
                    for fact in generation
                ),
                "review_action_count": len(review),
                "provider_call_count": provider_calls,
                "token_total": tokens,
                "coverage": "unavailable" if invalid_facts or (generation_all and not generation_coverage_complete) or (provider_all and not provider_facts_complete) else "complete",
                "unavailable_reason": (
                    _coverage_issue(invalid_facts[0])
                    if invalid_facts
                    else "accepted_artifact_count_zero" if not artifacts else "generation_attempt_incomplete" if generation_all and not generation_coverage_complete else "provider_telemetry_incomplete" if provider_all and not provider_facts_complete else None
                ),
                "source_observation_ids": sorted(fact["observation_id"] for fact in valid_facts),
            }
        )
    return result


def build_gold_cohort_effort(silver: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build one row per declared analytical cohort."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in build_gold_run_job_effort(silver):
        grouped[(str(row["cohort_id"]), str(row["cohort_type"]))].append(row)
    result: list[dict[str, Any]] = []
    for (cohort_id, cohort_type), rows in sorted(grouped.items()):
        provider_calls = _known_sum([row["provider_call_count"] for row in rows])
        tokens = _known_sum([row["token_total"] for row in rows])
        generation_rows = [row for row in rows if row.get("generation_observation_count") or row.get("generation_attempt_count")]
        eligible_rows = [row for row in generation_rows if row.get("eligible") is True]
        accepted_artifacts = sum(int(row["accepted_artifact_count"] or 0) for row in rows)
        generation_jobs = len(eligible_rows)
        first_pass_successes = sum(int(row["first_pass_success_count"] or 0) for row in eligible_rows)
        render_proofs = sum(int(row["render_proof_count"] or 0) for row in rows)
        verified_one_page = sum(int(row["verified_one_page_count"] or 0) for row in rows)
        accepted_rows = [row for row in rows if row.get("accepted_artifact_observation_count")]
        provider_rows = [row for row in rows if row.get("provider_attempt_count")]
        accepted_artifact_coverage = (
            "complete"
            if accepted_rows and all(row.get("accepted_artifact_coverage") == "complete" for row in accepted_rows)
            else "unavailable"
        )
        acceptance_evidence_coverage = (
            "unavailable"
            if any(
                row.get("accepted_artifact_observation_count")
                and row.get("accepted_artifact_coverage") != "complete"
                for row in rows
            )
            else "complete"
        )
        eligibility_coverage_complete = (
            bool(generation_rows)
            and all(
                row.get("eligible") in {True, False}
                and row.get("eligible_attempt_coverage") == "complete"
                for row in generation_rows
            )
        )
        generation_coverage_complete = (
            bool(generation_rows)
            and eligibility_coverage_complete
            and acceptance_evidence_coverage == "complete"
            and all(row.get("generation_attempt_coverage") == "complete" for row in eligible_rows)
        )
        provider_call_coverage = (
            "complete"
            if provider_rows and provider_calls is not None
            and accepted_artifact_coverage == "complete"
            and all(row.get("provider_call_coverage") == "complete" for row in provider_rows)
            else "unavailable"
        )
        token_coverage = (
            "complete"
            if provider_rows and tokens is not None
            and accepted_artifact_coverage == "complete"
            and all(row.get("token_coverage") == "complete" for row in provider_rows)
            else "unavailable"
        )
        result.append(
            {
                "schema_version": ANALYTICS_SCHEMA_VERSION,
                "metric": "gold_cohort_effort",
                "grain": "cohort",
                "cohort_id": cohort_id,
                "cohort_type": cohort_type,
                "attempted_job_count": len(rows),
                "generation_job_count": generation_jobs,
                "successful_run_job_count": sum(bool(row.get("accepted_artifact_count")) for row in eligible_rows),
                "eligible_attempt_coverage": "complete" if eligibility_coverage_complete and acceptance_evidence_coverage == "complete" else "unavailable",
                "accepted_artifact_count": accepted_artifacts,
                "first_pass_success_count": first_pass_successes,
                "first_pass_success_rate": first_pass_successes / generation_jobs if generation_jobs and generation_coverage_complete else None,
                "generation_attempt_coverage": "complete" if generation_coverage_complete else "unavailable",
                "verified_one_page_count": verified_one_page,
                "render_proof_count": render_proofs,
                "verified_one_page_rate": verified_one_page / render_proofs if render_proofs and all(row.get("render_proof_coverage") == "complete" for row in rows if row.get("accepted_artifact_count")) else None,
                "render_proof_coverage": "complete" if render_proofs and accepted_rows and all(row.get("render_proof_coverage") == "complete" for row in accepted_rows) else "unavailable",
                "accepted_artifact_observation_count": sum(int(row.get("accepted_artifact_observation_count") or 0) for row in rows),
                "accepted_artifact_coverage": accepted_artifact_coverage,
                "provider_call_coverage": provider_call_coverage,
                "token_coverage": token_coverage,
                "provider_call_count": provider_calls,
                "token_total": tokens,
                "per_accepted_artifact": (
                    {
                        "provider_call_count": provider_calls / accepted_artifacts,
                        "token_total": tokens / accepted_artifacts,
                    }
                    if accepted_artifacts and accepted_artifact_coverage == "complete" and provider_call_coverage == "complete" and token_coverage == "complete"
                    else None
                ),
                "coverage": "unavailable" if any(row.get("coverage") == "unavailable" for row in rows) else "complete",
                "unavailable_reason": next(
                    (str(row.get("unavailable_reason")) for row in rows if row.get("coverage") == "unavailable"),
                    None if accepted_artifacts else "accepted_artifact_count_zero",
                ),
                "source_run_job_ids": sorted(str(row["run_job_id"]) for row in rows),
            }
        )
    return result


def _cohort_key(payload: dict[str, Any]) -> tuple[str, str]:
    return str(payload.get("cohort_id") or "unknown"), str(payload.get("cohort_type") or "unknown")


def _posting_id(payload: dict[str, Any]) -> str:
    return str(payload.get("posting_id") or payload.get("job_id") or payload.get("source_id") or "").strip()


def _requirement_key(payload: dict[str, Any]) -> str:
    return str(payload.get("requirement") or payload.get("requirement_id") or "").strip()


def build_gold_requirement_demand(silver: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build one row per requirement and eligible opportunity cohort."""
    postings_by_cohort: dict[tuple[str, str], set[str]] = defaultdict(set)
    inventory_by_cohort: dict[tuple[str, str], set[str]] = defaultdict(set)
    requirement_postings: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    coverage_issues: dict[tuple[str, str], str] = {}
    inventory_cohorts: set[tuple[str, str]] = set()
    dimension_keys: set[tuple[str, str, str]] = set()
    for fact in silver:
        observation_type = fact.get("observation_type")
        if observation_type not in REQUIREMENT_DEMAND_OBSERVATION_TYPES | POSTING_INVENTORY_OBSERVATION_TYPES:
            continue
        payload = dict(fact.get("payload") or {})
        posting_id = _posting_id(payload)
        requirement = _requirement_key(payload)
        cohort = _cohort_key(payload)
        if observation_type in POSTING_INVENTORY_OBSERVATION_TYPES:
            inventory_cohorts.add(cohort)
        if observation_type in REQUIREMENT_DEMAND_OBSERVATION_TYPES and posting_id and requirement:
            dimension_keys.add((*cohort, requirement))
        if (issue := _coverage_issue(fact)) is not None:
            coverage_issues.setdefault(cohort, issue)
            continue
        if _eligibility(payload) is None:
            coverage_issues.setdefault(cohort, "eligibility_incomplete")
            continue
        if observation_type in POSTING_INVENTORY_OBSERVATION_TYPES:
            if posting_id and _eligibility(payload) is True:
                inventory_by_cohort[cohort].add(posting_id)
            continue
        if not posting_id or not requirement or _eligibility(payload) is not True:
            continue
        if cohort not in inventory_cohorts:
            postings_by_cohort[cohort].add(posting_id)
        requirement_postings[(*cohort, requirement)].add(posting_id)
    for cohort in inventory_cohorts:
        postings_by_cohort[cohort] = inventory_by_cohort[cohort]
    return [
        {
            "schema_version": ANALYTICS_SCHEMA_VERSION,
            "metric": "gold_requirement_demand",
            "grain": "requirement_and_cohort",
            "requirement": requirement,
            "cohort_id": cohort_id,
            "cohort_type": cohort_type,
            "numerator_posting_count": len(posting_ids),
            "denominator_posting_count": len(postings_by_cohort[(cohort_id, cohort_type)]),
            "coverage": "unavailable" if (cohort_id, cohort_type) in coverage_issues else "complete",
            "posting_inventory_coverage": "unavailable" if (cohort_id, cohort_type) in coverage_issues else "complete",
            "unavailable_reason": coverage_issues.get((cohort_id, cohort_type)),
        }
        for (cohort_id, cohort_type, requirement) in sorted(dimension_keys | set(requirement_postings))
        for posting_ids in [requirement_postings.get((cohort_id, cohort_type, requirement), set())]
    ]


def build_gold_candidate_gap(silver: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build one row per requirement, explicit gap category, and cohort."""
    denominator: dict[tuple[str, str, str, str, str], set[tuple[str, str]]] = defaultdict(set)
    gaps: dict[tuple[str, str, str, str, str, str, str], set[tuple[str, str]]] = defaultdict(set)
    coverage_issues: dict[tuple[str, str, str, str, str], str] = {}
    gap_keys: set[tuple[str, str, str, str]] = set()
    for fact in silver:
        observation_type = fact.get("observation_type")
        if observation_type not in REQUIREMENT_DEMAND_OBSERVATION_TYPES | CANDIDATE_GAP_OBSERVATION_TYPES:
            continue
        payload = dict(fact.get("payload") or {})
        posting_id = _posting_id(payload)
        requirement = _requirement_key(payload)
        cohort = _cohort_key(payload)
        category = str(payload.get("gap_category") or "").strip()
        profile = tuple(str(payload.get(field) or "") for field in (
            "candidate_profile_id", "candidate_profile_revision", "candidate_profile_fingerprint"
        ))
        partition = (*cohort, *profile)
        if observation_type in CANDIDATE_GAP_OBSERVATION_TYPES and posting_id and requirement and category in {"missing_evidence", "unmet_qualifier", "uncertain_interpretation"}:
            gap_keys.add((*cohort, requirement, category, *profile))
        if (issue := _coverage_issue(fact)) is not None:
            coverage_issues.setdefault(partition, issue)
            continue
        if _eligibility(payload) is None:
            coverage_issues.setdefault(partition, "eligibility_incomplete")
            continue
        if not posting_id or not requirement or _eligibility(payload) is not True:
            continue
        pair = (posting_id, requirement)
        if observation_type in REQUIREMENT_DEMAND_OBSERVATION_TYPES:
            denominator[partition].add(pair)
            continue
        if category in {"missing_evidence", "unmet_qualifier", "uncertain_interpretation"}:
            gaps[(*cohort, requirement, category, *profile)].add(pair)
    for key, pairs in list(gaps.items()):
        partition = key[:2] + key[4:]
        eligible_pairs = pairs & denominator[partition]
        if eligible_pairs != pairs:
            coverage_issues.setdefault(partition, "posting_requirement_coverage_incomplete")
        gaps[key] = eligible_pairs
    return [
        {
            "schema_version": ANALYTICS_SCHEMA_VERSION,
            "metric": "gold_candidate_gap",
            "grain": "requirement_and_gap_category_and_cohort",
            "requirement": requirement,
            "gap_category": category,
            "cohort_id": cohort_id,
            "cohort_type": cohort_type,
            "candidate_profile_id": profile_id or None,
            "candidate_profile_revision": profile_revision or None,
            "candidate_profile_fingerprint": profile_fingerprint or None,
            "numerator_requirement_count": len(pairs),
            "denominator_requirement_count": len(denominator[(cohort_id, cohort_type, profile_id, profile_revision, profile_fingerprint)]),
            "coverage": "unavailable" if (cohort_id, cohort_type, profile_id, profile_revision, profile_fingerprint) in coverage_issues else "complete",
            "candidate_requirement_coverage": "unavailable" if (cohort_id, cohort_type, profile_id, profile_revision, profile_fingerprint) in coverage_issues else "complete",
            "unavailable_reason": coverage_issues.get((cohort_id, cohort_type, profile_id, profile_revision, profile_fingerprint)),
        }
        for (cohort_id, cohort_type, requirement, category, profile_id, profile_revision, profile_fingerprint) in sorted(gap_keys | set(gaps))
        for pairs in [gaps.get((cohort_id, cohort_type, requirement, category, profile_id, profile_revision, profile_fingerprint), set())]
    ]


def build_gold_semantic_metric(
    gold: dict[str, list[dict[str, Any]]],
    registry: dict[str, Any],
    *,
    source_commit: str,
    input_fingerprint: str,
) -> list[dict[str, Any]]:
    """Materialize registry formulas as one canonical metric relation."""
    output: list[dict[str, Any]] = []
    for definition in registry.get("metrics") or []:
        metric_id = str(definition["metric_id"])
        source_name = str(definition["source_model"])
        numerator_field = str(definition["numerator_field"])
        denominator_field = str(definition["denominator_field"])
        coverage_field = str(definition["coverage_metric"])
        dimension_fields = [str(field) for field in definition.get("dimension_fields") or []]
        rows = list(gold.get(source_name) or []) or [{
            "cohort_id": "__unavailable__",
            "cohort_type": "__unavailable__",
        }]
        for row in rows:
            numerator = row.get(numerator_field)
            denominator = row.get(denominator_field)
            coverage_value = row.get(coverage_field)
            if coverage_value is None:
                coverage_value = row.get("coverage")
            coverage_status = "complete" if str(coverage_value or "complete").lower() == "complete" else "unavailable"
            unavailable_reason = row.get("unavailable_reason")
            if denominator in (None, 0):
                coverage_status = "unavailable"
                unavailable_reason = unavailable_reason or "denominator_zero_or_missing"
            if numerator is None:
                coverage_status = "unavailable"
                unavailable_reason = unavailable_reason or "numerator_missing"
            value = (
                float(numerator) / float(denominator)
                if coverage_status == "complete" and denominator not in (None, 0) and numerator is not None
                else None
            )
            dimension_key = ":".join(
                str(row.get(field) or "__unavailable__") for field in dimension_fields
            ) or str(row.get("cohort_id") or "__unavailable__")
            semantic = {
                "metric_id": metric_id,
                "metric_version": int(definition["version"]),
                "cohort_id": row.get("cohort_id"),
                "cohort_type": row.get("cohort_type"),
                "dimension_key": dimension_key,
                "numerator": numerator,
                "denominator": denominator,
                "value": value,
                "coverage_status": coverage_status,
                "coverage_numerator": denominator if coverage_status == "complete" else 0,
                "coverage_denominator": denominator,
                "unavailable_reason": unavailable_reason,
                "source_commit": source_commit,
                "input_fingerprint": input_fingerprint,
            }
            semantic["material_digest"] = _digest(semantic)
            output.append(semantic)
    return sorted(output, key=lambda row: (row["metric_id"], str(row["cohort_id"]), row["dimension_key"]))


def build_gold_cv_effort(silver: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compatibility adapter for callers migrating to run-job Gold."""
    rows = build_gold_run_job_effort(silver)
    for row in rows:
        accepted_count = int(row.get("accepted_artifact_count") or 0)
        provider_calls = row.get("provider_call_count")
        tokens = row.get("token_total")
        row["per_accepted_artifact"] = (
            {
                "provider_call_count": provider_calls / accepted_count,
                "token_total": tokens / accepted_count,
            }
            if accepted_count and provider_calls is not None and tokens is not None
            else None
        )
        row["metric"] = "gold_cv_effort_compat"
    return rows


def build_gold_acceptance_state(
    registry: dict[str, Any],
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    records = list(registry.get("records") or [])
    mapping = dict(registry.get("claim_priority_map") or {})
    if not mapping:
        mapping = load_metric_registry().get("claim_priority_map", {})
    status_dimensions = dict(state.get("status_dimensions") or {})
    records_by_priority: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        claim = str(record.get("claim") or "")
        priorities = mapping.get(claim)
        if not priorities:
            raise ValueError(f"analytics_claim_priority_mapping_missing:{claim}")
        for priority in priorities:
            records_by_priority[str(priority)].append(record)
    output: list[dict[str, Any]] = []
    priorities = sorted(set(records_by_priority) | set(status_dimensions))
    for priority in priorities:
        dimension = dict(status_dimensions.get(priority) or {})
        priority_records = records_by_priority.get(priority) or [None]
        for record in sorted(priority_records, key=lambda item: str((item or {}).get("evidence_id") or "")):
            record = record or {}
            evidence_id = record.get("evidence_id")
            output.append({
                "schema_version": ANALYTICS_SCHEMA_VERSION,
                "metric": "gold_acceptance_state",
                "grain": "priority + evidence_id",
                "row_key": f"{priority}:{evidence_id or '__status_only__'}",
                "priority": priority,
                "evidence_id": evidence_id,
                "claim": record.get("claim"),
                "evidence_status": record.get("status"),
                "cohort_id": record.get("cohort_id"),
                "cohort_type": record.get("cohort_type"),
                "source_commit": record.get("source_commit"),
                "declared_input_fingerprint": record.get("declared_input_fingerprint"),
                "material_metrics_sha256": record.get("material_metrics_sha256"),
                "implementation_status": dimension.get("implementation_status"),
                "acceptance_status": dimension.get("acceptance_status"),
                "measurement_status": dimension.get("measurement_status"),
                "historical": record.get("status") in {"historical", "superseded"},
                "deferred": record.get("status") == "deferred" or dimension.get("implementation_status") == "deferred" or dimension.get("acceptance_status") == "deferred",
            })
    return output


def build_gold_optimization_state(
    registry: dict[str, Any],
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = build_gold_acceptance_state(registry, state)
    dimensions = dict(state.get("status_dimensions") or {})
    return [
        {
            "schema_version": ANALYTICS_SCHEMA_VERSION,
            "metric": "gold_optimization_state",
            "grain": row["grain"],
            "row_key": row["row_key"],
            "priority": row["priority"],
            "evidence_id": row["evidence_id"],
            "claim": row["claim"],
            "evidence_status": row["evidence_status"],
            "measurement_status": dimensions.get(row["priority"], {}).get("measurement_status"),
            "optimization_status": dimensions.get(row["priority"], {}).get("optimization_status"),
            "deferred": dimensions.get(row["priority"], {}).get("optimization_status") == "deferred",
        }
        for row in rows
        if dimensions.get(row["priority"], {}).get("optimization_status") is not None
    ]


def material_gold_digest(gold: dict[str, Any]) -> str:
    return _digest({key: value for key, value in gold.items() if key not in {"generated_at", "ingested_at"}})


def _insert_json_rows(connection: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> None:
    connection.execute(f'DROP TABLE IF EXISTS "{table}"')
    connection.execute(f'CREATE TABLE "{table}" (payload_json TEXT NOT NULL)')
    connection.executemany(
        f'INSERT INTO "{table}" (payload_json) VALUES (?)',
        [(_json(row),) for row in rows],
    )


def write_analytics_sqlite(
    *,
    path: Path,
    artifacts: list[dict[str, Any]],
    run_jobs: list[dict[str, Any]],
    cohorts: list[dict[str, Any]],
    acceptance: list[dict[str, Any]],
    requirement_demand: list[dict[str, Any]] | None = None,
    candidate_gaps: list[dict[str, Any]] | None = None,
    optimization: list[dict[str, Any]] | None = None,
    semantic_metrics: list[dict[str, Any]] | None = None,
) -> None:
    """Write disposable analytical projections and rebuild SQL views deterministically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        _insert_json_rows(connection, "silver_cv_artifact", artifacts)
        _insert_json_rows(connection, "silver_run_job_effort", run_jobs)
        _insert_json_rows(connection, "silver_cohort_effort", cohorts)
        _insert_json_rows(connection, "silver_requirement_demand", requirement_demand or [])
        _insert_json_rows(connection, "silver_candidate_gap", candidate_gaps or [])
        _insert_json_rows(connection, "silver_acceptance_evidence", acceptance)
        _insert_json_rows(connection, "silver_optimization_state", optimization or [])
        _insert_json_rows(connection, "gold_semantic_metric_rows", semantic_metrics or [])
        connection.executescript(
            (Path(__file__).resolve().parent / "sql/fitcv_gold_views.sql").read_text(encoding="utf-8")
        )


def rebuild_analytics_bundle(
    bundle: dict[str, Any],
    *,
    source_commit: str,
    declared_input_fingerprint: str,
    ingested_at: str,
) -> dict[str, Any]:
    sources = dict(bundle.get("sources") or {})
    bronze = build_bronze_observations(
        sources,
        source_commit=source_commit,
        declared_input_fingerprint=declared_input_fingerprint,
        ingested_at=ingested_at,
    )
    silver = build_silver_facts(bronze)
    artifacts = build_gold_cv_artifact(silver)
    run_jobs = build_gold_run_job_effort(silver)
    cohorts = build_gold_cohort_effort(silver)
    requirement_demand = build_gold_requirement_demand(silver)
    candidate_gaps = build_gold_candidate_gap(silver)
    registry = dict(bundle.get("registry") or {})
    if not registry.get("metrics"):
        registry["metrics"] = load_metric_registry().get("metrics", [])
    acceptance = build_gold_acceptance_state(registry, dict(bundle.get("state") or {}))
    optimization = build_gold_optimization_state(
        registry,
        dict(bundle.get("state") or {}),
    )
    material = {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "gold_cv_artifact": artifacts,
        "gold_run_job_effort": run_jobs,
        "gold_cohort_effort": cohorts,
        "gold_requirement_demand": requirement_demand,
        "gold_candidate_gap": candidate_gaps,
        "gold_acceptance_state": acceptance,
        "gold_optimization_state": optimization,
    }
    material["gold_semantic_metric"] = build_gold_semantic_metric(
        material,
        registry,
        source_commit=source_commit,
        input_fingerprint=declared_input_fingerprint,
    )
    return {
        "schema_version": ANALYTICS_SCHEMA_VERSION,
        "source_commit": source_commit,
        "declared_input_fingerprint": declared_input_fingerprint,
        "ingested_at": ingested_at,
        "bronze": bronze,
        "silver": silver,
        "gold": material,
        "material_metrics_sha256": _digest(material),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Declared analytics source bundle JSON")
    parser.add_argument("--output", type=Path, required=True, help="Deterministic analytics output JSON")
    parser.add_argument("--sqlite-output", type=Path, help="Disposable analytical SQLite projection")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--declared-input-fingerprint", required=True)
    parser.add_argument("--ingested-at", required=True)
    args = parser.parse_args()
    bundle = json.loads(args.input.read_text(encoding="utf-8"))
    output = rebuild_analytics_bundle(
        bundle,
        source_commit=args.source_commit,
        declared_input_fingerprint=args.declared_input_fingerprint,
        ingested_at=args.ingested_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.sqlite_output:
        write_analytics_sqlite(
            path=args.sqlite_output,
            artifacts=output["gold"]["gold_cv_artifact"],
            run_jobs=output["gold"]["gold_run_job_effort"],
            cohorts=output["gold"]["gold_cohort_effort"],
            requirement_demand=output["gold"]["gold_requirement_demand"],
            candidate_gaps=output["gold"]["gold_candidate_gap"],
            acceptance=output["gold"]["gold_acceptance_state"],
            optimization=output["gold"]["gold_optimization_state"],
            semantic_metrics=output["gold"]["gold_semantic_metric"],
        )
    print(json.dumps({"status": "ok", "material_metrics_sha256": output["material_metrics_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
