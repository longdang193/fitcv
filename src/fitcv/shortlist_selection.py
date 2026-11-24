"""Deterministic requirement-aware shortlist coverage and admission."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any, Iterable, Mapping

from fitcv.contracts import (
    SHORTLIST_REQUIREMENT_CONTRACT_VERSION,
    RequirementOccurrence,
    build_requirement_occurrences,
)

COVERAGE_STATES = frozenset({"S", "P", "E", "U"})
ADMISSION_CAPACITY = 50
SHORTLIST_POLICY_VERSION = "shortlist_policy_v1"


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _state_for_evidence(item: Mapping[str, Any]) -> str:
    support_status = _norm(item.get("support_status") or item.get("support_state"))
    qualifier_status = _norm(item.get("qualifier_status"))
    status = _norm(item.get("coverage_state") or item.get("shortlist_state") or support_status or item.get("status"))
    if status == "not_selected" and (
        item.get("verified")
        or item.get("verified_support")
        or support_status in {"verified", "supported", "qualified", "confirmed"}
    ):
        return "S"
    if qualifier_status in {"qualifier_only", "qualifier_only_support", "unverified"} and support_status in {
        "supported",
        "verified",
        "qualified",
        "confirmed",
    }:
        return "P"
    if status in {"s", "supported", "verified", "qualified", "confirmed"}:
        return "S"
    if status in {"p", "partial", "qualifier_only", "qualifier_only_support", "unverified"}:
        return "P"
    if status in {"u", "unknown", "pending", "unresolved", "assessment_failed", "retrieval_failed", "failure"}:
        return "U"
    if status in {"e", "unsupported", "no_support", "not_evidenced", "reviewed_no_support", "absent"}:
        return "E" if bool(item.get("reviewed", True)) else "U"
    if item.get("assessment_failed") or item.get("pending") or item.get("unresolved"):
        return "U"
    if item.get("reviewed") and item.get("no_support"):
        return "E"
    return "U"


def _is_contradiction(item: Mapping[str, Any]) -> bool:
    return bool(
        item.get("contradiction")
        or item.get("contradicted")
        or _norm(item.get("qualifier_status")) in {"contradicted", "qualifier_failure", "failed"}
        or _norm(item.get("support_status")) in {"contradicted", "qualifier_failure"}
    )


def _provenance(item: Mapping[str, Any]) -> int:
    value = item.get("provenance_grade", item.get("evidence_validity_provenance", item.get("provenance")))
    if isinstance(value, bool):
        return int(value)
    try:
        return max(0, min(3, int(value)))
    except (TypeError, ValueError):
        return 1 if item.get("evidence_id") else 0


def _requirement_reference_variants(value: Any) -> set[str]:
    reference = str(value or "").strip().casefold()
    if not reference:
        return set()
    normalized = reference.replace("-", "_").replace(" ", "_")
    variants = {reference, normalized}
    if normalized.startswith("required_skill_instance:"):
        skill_reference = normalized.split(":", 1)[1].rsplit(":", 1)[0]
        variants.add(f"required_skill:{skill_reference}")
    return variants


_AUTHORITATIVE_ID_FIELDS = (
    "occurrence_id",
    "requirement_id",
    "source_requirement_id",
    "requirement_instance_id",
)
_RELATED_ID_FIELDS = (
    "requirement_ids",
    "canonical_requirement_ids",
    "supported_requirement_ids",
)


def _authoritative_reference_variants(item: Mapping[str, Any]) -> set[str]:
    values: list[Any] = [item.get(key) for key in _AUTHORITATIVE_ID_FIELDS]
    for key in _RELATED_ID_FIELDS:
        related = item.get(key)
        if isinstance(related, (list, tuple, set)):
            values.extend(related)
        elif related:
            values.append(related)
    return {
        variant
        for value in values
        for variant in _requirement_reference_variants(value)
    }


def _matches(
    item: Mapping[str, Any],
    occurrence: RequirementOccurrence,
    *,
    wording_is_unique: bool = False,
) -> bool:
    item_reference_variants = _authoritative_reference_variants(item)
    occurrence_ids = {occurrence.occurrence_id, occurrence.source_requirement_id or ""}
    occurrence_reference_variants = {
        variant
        for occurrence_id in occurrence_ids
        if occurrence_id
        for variant in _requirement_reference_variants(occurrence_id)
    }
    if item_reference_variants & occurrence_reference_variants:
        return True
    # An explicit but unrelated identity is authoritative; wording must not leak it.
    if item_reference_variants:
        return False
    wording = _norm(item.get("requirement") or item.get("source_wording"))
    return bool(wording_is_unique and wording and wording == _norm(occurrence.source_wording))


def _combine(states: list[str], operator: str | None) -> str:
    if not states:
        return "U"
    if operator == "AND":
        if all(state == "S" for state in states):
            return "S"
        if any(state == "U" for state in states):
            return "U"
        if any(state in {"S", "P"} for state in states):
            return "P"
        return "E"
    if operator == "OR":
        if any(state == "S" for state in states):
            return "S"
        if any(state == "P" for state in states):
            return "P"
        if any(state == "U" for state in states):
            return "U"
        return "E"
    if "S" in states:
        return "S"
    if "P" in states:
        return "P"
    if "U" in states:
        return "U"
    return "E"


def assess_requirement_occurrences(
    occurrences: Iterable[RequirementOccurrence],
    evidence: Iterable[Mapping[str, Any]],
    *,
    assessment_complete: bool = True,
) -> list[dict[str, Any]]:
    occurrence_list = list(occurrences)
    evidence_list = list(evidence)
    by_id = {item.occurrence_id: item for item in occurrence_list}
    compound_child_ids = {
        child_id
        for occurrence in occurrence_list
        for child_id in occurrence.child_occurrence_ids
    }
    top_level_occurrences = [
        occurrence
        for occurrence in occurrence_list
        if occurrence.occurrence_id not in compound_child_ids
    ]
    wording_counts: dict[str, int] = defaultdict(int)
    for occurrence in top_level_occurrences:
        wording = _norm(occurrence.source_wording)
        if wording:
            wording_counts[wording] += 1
    results: dict[str, dict[str, Any]] = {}

    def assess(occurrence: RequirementOccurrence, stack: tuple[str, ...] = ()) -> dict[str, Any]:
        if occurrence.occurrence_id in results:
            return results[occurrence.occurrence_id]
        if occurrence.occurrence_id in stack:
            raise ValueError(f"compound requirement cycle at {occurrence.occurrence_id}")
        children = [by_id[child_id] for child_id in occurrence.child_occurrence_ids if child_id in by_id]
        if children:
            child_results = [assess(child, (*stack, occurrence.occurrence_id)) for child in children]
            state = _combine([str(result["state"]) for result in child_results], occurrence.compound_operator)
            if occurrence.compound_operator == "OR":
                best_rank = max({"S": 3, "P": 2, "E": 1, "U": 1}.get(str(result["state"]), 1) for result in child_results)
                satisfying_paths = [
                    result
                    for result in child_results
                    if {"S": 3, "P": 2, "E": 1, "U": 1}.get(str(result["state"]), 1) == best_rank
                ]
            else:
                satisfying_paths = child_results
            evidence_ids = sorted({evidence_id for result in satisfying_paths for evidence_id in result["evidence_ids"]})
            contradiction = any(result["contradiction"] for result in satisfying_paths)
            provenance = min((int(result["provenance"]) for result in satisfying_paths), default=0)
            result = {
                "occurrence_id": occurrence.occurrence_id,
                "category": occurrence.category,
                "state": state,
                "evidence_ids": evidence_ids,
                "contradiction": contradiction,
                "qualifier_failure": any(result["qualifier_failure"] for result in satisfying_paths),
                "provenance": provenance,
                "compound_child": occurrence.occurrence_id in compound_child_ids,
                "compound_operator": occurrence.compound_operator,
                "satisfying_child_ids": [result["occurrence_id"] for result in satisfying_paths],
            }
            results[occurrence.occurrence_id] = result
            return result
        matches = [
            item
            for item in evidence_list
            if _matches(
                item,
                occurrence,
                wording_is_unique=(
                    occurrence.occurrence_id not in compound_child_ids
                    and wording_counts.get(_norm(occurrence.source_wording), 0) == 1
                ),
            )
        ]
        states = [_state_for_evidence(item) for item in matches]
        state = _combine(states, None) if matches else ("E" if assessment_complete else "U")
        result = {
            "occurrence_id": occurrence.occurrence_id,
            "category": occurrence.category,
            "state": state,
            "evidence_ids": sorted({str(item.get("evidence_id") or "") for item in matches if item.get("evidence_id")}),
            "contradiction": any(_is_contradiction(item) for item in matches),
            "qualifier_failure": any(_norm(item.get("qualifier_status")) in {"contradicted", "qualifier_failure", "failed"} for item in matches),
            "provenance": min((_provenance(item) for item in matches), default=0),
            "compound_child": occurrence.occurrence_id in compound_child_ids,
        }
        results[occurrence.occurrence_id] = result
        return result

    return [assess(occurrence) for occurrence in occurrence_list]


def _category_summary(results: list[Mapping[str, Any]], category: str) -> dict[str, Any]:
    values = [
        result
        for result in results
        if str(result.get("category") or "") == category
        and not result.get("compound_child")
    ]
    counts = {"supported": 0, "partial": 0, "not_evidenced": 0, "unknown": 0}
    for result in values:
        state = str(result.get("state") or "U")
        counts[{"S": "supported", "P": "partial", "E": "not_evidenced", "U": "unknown"}.get(state, "unknown")] += 1
    total = len(values)
    return {**counts, "total": total, "ratio": (counts["supported"] / total if total else None), "active": bool(total)}


def build_coverage_summary(results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(result) for result in results]
    top_level_rows = [row for row in rows if not row.get("compound_child")]
    compound_diagnostics = [row for row in rows if row.get("compound_child")]
    categories = {category: _category_summary(rows, category) for category in ("required", "duties", "preferred")}
    active_core = [categories[category] for category in ("required", "duties") if categories[category]["active"]]
    active_results = [
        result
        for result in top_level_rows
        if str(result.get("category") or "") in {"required", "duties", "preferred"}
    ]
    total = len(active_results)
    supported = sum(str(result.get("state")) == "S" for result in active_results)
    partial = sum(str(result.get("state")) == "P" for result in active_results)
    not_evidenced = sum(str(result.get("state")) == "E" for result in active_results)
    unknown = sum(str(result.get("state")) == "U" for result in active_results)
    return {
        "required": categories["required"],
        "duties": categories["duties"],
        "preferred": categories["preferred"],
        "active_core_mask": {"required": categories["required"]["active"], "duties": categories["duties"]["active"]},
        "balanced_core_support": min((float(metric["ratio"]) for metric in active_core), default=None),
        "assessment_completeness": ((supported + partial + not_evidenced) / total if total else 1.0),
        "unknown_rate": (unknown / total if total else 0.0),
        "evidence_validity_provenance": min((int(result.get("provenance") or 0) for result in top_level_rows if str(result.get("category") or "") in {"required", "duties"}), default=0),
        "confirmed_critical_gaps": len({
            str(result.get("occurrence_id"))
            for result in top_level_rows
            if str(result.get("category") or "") in {"required", "duties"}
            and (result.get("contradiction") or result.get("qualifier_failure"))
        }),
        "total": total,
        "states": top_level_rows,
        "compound_diagnostics": compound_diagnostics,
    }


def _ratio(summary: Mapping[str, Any], category: str) -> float | None:
    value = (summary.get(category) or {}).get("ratio")
    return None if value is None else float(value)


def dominates(lhs: Mapping[str, Any], rhs: Mapping[str, Any]) -> bool:
    left = lhs.get("coverage") or lhs.get("coverage_summary") or {}
    right = rhs.get("coverage") or rhs.get("coverage_summary") or {}
    if left.get("active_core_mask") != right.get("active_core_mask"):
        return False
    metrics = [_ratio(left, category) for category in ("required", "duties") if _ratio(left, category) is not None]
    other = [_ratio(right, category) for category in ("required", "duties") if _ratio(right, category) is not None]
    if not metrics or len(metrics) != len(other):
        return False
    return all(a >= b for a, b in zip(metrics, other)) and any(a > b for a, b in zip(metrics, other))


def build_pareto_fronts(rows: Iterable[Mapping[str, Any]]) -> list[list[dict[str, Any]]]:
    remaining = [dict(row) for row in rows]
    fronts: list[list[dict[str, Any]]] = []
    while remaining:
        front = [row for row in remaining if not any(dominates(other, row) for other in remaining if other is not row)]
        front.sort(key=lambda row: str(row.get("canonical_job_identity") or row.get("job_url") or ""))
        fronts.append(front)
        front_ids = {id(row) for row in front}
        remaining = [row for row in remaining if id(row) not in front_ids]
    return fronts


def _sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    coverage = row.get("coverage") or row.get("coverage_summary") or {}
    preferred = _ratio(coverage, "preferred")
    return (
        -int(coverage.get("evidence_validity_provenance") or 0),
        int(coverage.get("confirmed_critical_gaps") or 0),
        -(preferred if preferred is not None else -1.0),
        str(row.get("canonical_job_identity") or row.get("job_url") or ""),
    )


def select_requirement_aware_jobs(
    rows: Iterable[Mapping[str, Any]],
    *,
    capacity: int = ADMISSION_CAPACITY,
) -> dict[str, Any]:
    if capacity < 0:
        raise ValueError("capacity must be non-negative")
    source_rows = [dict(row) for row in rows]
    evaluation_pool_id = hashlib.sha256(
        json.dumps(
            sorted(
                (
                    {
                        "canonical_job_identity": row.get("canonical_job_identity") or row.get("job_url"),
                        "job_url": row.get("job_url"),
                    }
                    for row in source_rows
                ),
                key=lambda item: (str(item["canonical_job_identity"] or ""), str(item["job_url"] or "")),
            ),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    fronts = build_pareto_fronts(source_rows)
    ordered: list[dict[str, Any]] = []
    for front_number, front in enumerate(fronts, start=1):
        for row in sorted(front, key=_sort_key):
            row["pareto_front"] = front_number
            ordered.append(row)
    admitted = ordered[:capacity]
    admitted_ids = {id(row) for row in admitted}
    for rank, row in enumerate(ordered, start=1):
        row["admission_rank"] = rank
        row["admitted"] = id(row) in admitted_ids
        row["admission_reason"] = f"pareto_front_{row['pareto_front']}" if row["admitted"] else None
        row["exclusion_reason"] = None if row["admitted"] else "capacity_exceeded"
    assessment_payload = [
        {
            "canonical_job_identity": row.get("canonical_job_identity") or row.get("job_url"),
            "states": [
                {
                    key: state.get(key)
                    for key in ("occurrence_id", "state", "contradiction", "qualifier_failure", "evidence_ids", "provenance")
                }
                for state in (row.get("coverage") or {}).get("states", [])
            ],
        }
        for row in ordered
    ]
    assessment_fingerprint = hashlib.sha256(
        json.dumps(assessment_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    fingerprint_payload = [
        {key: row.get(key) for key in ("canonical_job_identity", "job_url", "admitted", "admission_rank", "pareto_front")}
        for row in ordered
    ]
    fingerprint = hashlib.sha256(json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "strategy": "core_pareto_evidence_v1",
        "admission_capacity": capacity,
        "rows": ordered,
        "admitted": admitted,
        "non_admitted": [row for row in ordered if not row["admitted"]],
        "front_count": len(fronts),
        "evaluation_pool_id": evaluation_pool_id,
        "decision_fingerprint": fingerprint,
        "assessment_fingerprint": assessment_fingerprint,
        "policy_version": SHORTLIST_POLICY_VERSION,
        "requirement_contract_version": SHORTLIST_REQUIREMENT_CONTRACT_VERSION,
    }


def build_requirement_aware_rows(
    jobs: Iterable[Mapping[str, Any]],
    evidence_by_job: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    *,
    assessment_complete: bool = True,
) -> list[dict[str, Any]]:
    evidence_map = evidence_by_job or {}
    rows: list[dict[str, Any]] = []
    for job in jobs:
        identity = str(job.get("canonical_job_identity") or job.get("job_url") or job.get("source_job_id") or "").strip()
        existing_coverage = job.get("coverage") or job.get("coverage_summary")
        if isinstance(existing_coverage, Mapping):
            rows.append({**dict(job), "canonical_job_identity": identity, "coverage": dict(existing_coverage)})
            continue
        occurrences = build_requirement_occurrences(job, job_identity=identity)
        job_evidence = evidence_map.get(identity, [])
        if not job_evidence and isinstance(job.get("requirement_coverage"), list):
            job_evidence = []
            for item in job.get("requirement_coverage"):
                if not isinstance(item, Mapping):
                    continue
                requirement_id = (
                    item.get("occurrence_id")
                    or item.get("requirement_instance_id")
                    or item.get("requirement_id")
                    or item.get("source_requirement_id")
                )
                status = _norm(item.get("selected_support") or item.get("status") or item.get("support_status"))
                if status in {"relevant_unverified", "qualifier_only"}:
                    support_status = "partial"
                else:
                    support_status = status or "unknown"
                evidence_ids = [
                    str(evidence_id).strip()
                    for evidence_id in (
                        list(item.get("supporting_evidence_ids") or [])
                        + list(item.get("pool_supporting_evidence_ids") or [])
                        + list(item.get("evidence_refs") or [])
                    )
                    if str(evidence_id).strip()
                ] or [str(item.get("evidence_id") or "").strip()]
                for evidence_id in dict.fromkeys(evidence_ids):
                    job_evidence.append(
                        {
                            "occurrence_id": requirement_id,
                            "requirement_id": item.get("requirement_id"),
                            "support_status": support_status,
                            "qualifier_status": item.get("qualifier_status"),
                            "evidence_id": evidence_id or None,
                            "reviewed": item.get("reviewed", True),
                            "verified": status in {"verified", "not_selected"},
                            "contradiction": item.get("contradicted") or item.get("contradiction"),
                        }
                    )
        assessments = assess_requirement_occurrences(occurrences, job_evidence, assessment_complete=assessment_complete)
        rows.append({**dict(job), "canonical_job_identity": identity, "coverage": build_coverage_summary(assessments)})
    return rows
