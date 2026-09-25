"""Benchmark requirement-specific evidence support without external services."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from fitcv import evidence as evidence_module
from fitcv.agentic_cv_analysis import analyze_ranked_job
from fitcv.cv_generator import build_generation_prompt
from fitcv.evidence import (
    _annotate_requirement_support,
    build_required_skill_descriptors,
    retrieve_evidence_bundle,
)
from fitcv.validator import AnalysisGroundingPayload, run_all_validations

DEFAULT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "requirement_support_benchmark.json"
DEFAULT_POLICY = REPO_ROOT / "config" / "policy" / "cv_analysis.yaml"
MEASURED_RUNS = 5
WARMUP_RUNS = 1
EXPECTED_SUPPORT_PAIRS = {
    ("required_skill:sql", "ev-broad"),
    ("required_skill:sql", "ev-a-sql"),
    ("required_skill:python", "ev-b-python"),
}


def _item(evidence_id: str, skills: list[str], text: str) -> dict[str, object]:
    return {
        "schema_version": "candidate-evidence.v1",
        "evidence_id": evidence_id,
        "kind": "project",
        "title": evidence_id,
        "text": text,
        "source_section": "projects",
        "parent_id": evidence_id,
        "source_refs": [{"document_id": f"doc-{evidence_id}"}],
        "evidence_type": "candidate_evidence",
        "name": evidence_id,
        "skills": skills,
        "scoring_context": text,
        "business_value": text,
        "role": "Data Engineer",
        "company": "Example",
    }


def _support_pairs(support: dict[str, list[str]]) -> set[tuple[str, str]]:
    return {
        (str(requirement_id), str(evidence_id))
        for requirement_id, evidence_ids in support.items()
        for evidence_id in evidence_ids
    }


def _recall_probe(channel_pool_size: int) -> dict[str, object]:
    profile = {
        "schema_version": "candidate-profile.v2",
        "_projected_evidence_pool": [
            _item(f"ev-{letter}", [], "Python")
            for letter in ("a", "b", "c", "d")
        ]
        + [_item("ev-target", ["Python"], "Candidate evidence")],
    }
    started = time.perf_counter()
    bundle = retrieve_evidence_bundle(
        profile,
        {"required_skills": ["Python"]},
        1,
        config={
            "cv_analysis": {
                "semantic_alignment": {
                    "enabled": False,
                    "channel_pool_size": channel_pool_size,
                }
            }
        },
    )
    retrieval_latency_ms = time.perf_counter() - started
    support = dict(bundle.get("requirement_support") or {})
    return {
        "channel_pool_size": channel_pool_size,
        "canonical_support": dict(support.get("canonical") or {}),
        "retrieved_support": dict(support.get("pool") or {}),
        "selected_support": dict(support.get("selected") or {}),
        "selected_evidence_ids": list(bundle.get("selected_evidence_ids") or []),
        "retrieval_latency_ms": round(retrieval_latency_ms * 1000, 3),
        "selected_context_chars": sum(
            len(str(item.get("text") or ""))
            for item in list(bundle.get("selected_evidence") or [])
        ),
    }


def _annotation_cost_probe() -> dict[str, object]:
    items = [_item(f"ev-{letter}", ["Python"], "Python") for letter in ("a", "b", "c", "d", "e")]
    descriptors = build_required_skill_descriptors({"required_skills": ["Python"]})
    runs = 100
    started = time.perf_counter()
    for _ in range(runs):
        _annotate_requirement_support(copy.deepcopy(items), descriptors, None)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "runs": runs,
        "items_per_run": len(items),
        "mean_annotation_latency_ms": round(elapsed_ms / runs, 3),
    }


def _recall_experiment() -> dict[str, object]:
    return {
        "current_pool": _recall_probe(4),
        "larger_pool": _recall_probe(8),
        "annotation_cost_probe": _annotation_cost_probe(),
        "production_defaults_changed": False,
    }


def run(weight: float) -> dict[str, object]:
    """Preserve prior requirement-aware benchmark contract."""
    profile = {
        "schema_version": "candidate-profile.v2",
        "_projected_evidence_pool": [
            _item("ev-broad", ["SQL"], "SQL Python"),
            _item("ev-a-sql", ["SQL"], "SQL"),
            _item("ev-b-python", ["Python"], "Python"),
        ],
    }
    job = {
        "required_skills": ["SQL", "Python"],
        "required_skill_entities": [
            {"raw_text": "SQL", "canonical": "sql"},
            {"raw_text": "Python", "canonical": "python"},
        ],
    }
    config = {
        "cv_analysis": {
            "semantic_alignment": {"enabled": False},
            "selection_policy": {"requirement_gain_weight": weight},
        }
    }
    started = time.perf_counter()
    bundle = retrieve_evidence_bundle(profile, job, 2, config=config)
    retrieval_ms = (time.perf_counter() - started) * 1000
    selected = list(bundle.get("selected_evidence") or [])
    support = dict(bundle.get("requirement_support") or {})
    canonical_support = dict(support.get("canonical") or {})
    selected_support = dict(support.get("selected") or {})
    pool_support = dict(support.get("pool") or {})
    canonical_requirements = sorted(key for key, ids in canonical_support.items() if ids)
    verified_requirements = sorted(key for key, ids in selected_support.items() if ids)
    distinct_pool_requirements = sorted(key for key, ids in pool_support.items() if ids)
    selected_ids = [str(item.get("evidence_id") or "") for item in selected]
    requirement_coverage = [
        {
            "requirement": requirement_id.removeprefix("required_skill:"),
            "canonical_skill": requirement_id.removeprefix("required_skill:"),
            "selected_support": "verified" if ids else "unsupported",
            "supporting_evidence_ids": list(ids),
        }
        for requirement_id, ids in sorted(selected_support.items())
    ]
    prompt_started = time.perf_counter()
    prompt = build_generation_prompt(
        jd=job,
        evidence=selected,
        gap={"requirement_coverage": requirement_coverage},
        template="## Skills\n...",
    )
    prompt_latency_ms = (time.perf_counter() - prompt_started) * 1000
    validation_started = time.perf_counter()
    validation = run_all_validations(
        "## Skills\nSQL\n",
        {"skills": [{"name": "SQL"}], "experiences": [], "projects": []},
        {
            "required_cv_sections": ["Skills"],
            "cv_max_pages": 2,
            "cv": {"validation": {"allow_profile_skill_outside_selected_evidence": True}},
        },
        analysis_grounding={"evidence_payload": selected, "requirement_coverage": requirement_coverage},
    )
    validation_latency_ms = (time.perf_counter() - validation_started) * 1000
    selected_pairs = _support_pairs(selected_support)
    return {
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip(),
        "weight": weight,
        "metrics": {
            "verified_requirement_coverage": len(verified_requirements),
            "canonical_requirement_coverage": len(canonical_requirements),
            "pool_requirement_coverage": len(distinct_pool_requirements),
            "incorrect_assignments": len(selected_pairs - EXPECTED_SUPPORT_PAIRS),
            "duplicate_evidence": len(selected_ids) - len(set(selected_ids)),
            "retrieved_count": len(selected),
            "provider_calls": 0,
            "estimated_input_tokens": len(prompt) // 4,
            "retrieval_latency_ms": round(retrieval_ms, 3),
            "prompt_build_latency_ms": round(prompt_latency_ms, 3),
            "validation_latency_ms": round(validation_latency_ms, 3),
            "grounding_failures": len(validation.get("grounding_violations") or []),
        },
        "selected_evidence_ids": selected_ids,
        "expected_support_pairs": sorted(EXPECTED_SUPPORT_PAIRS),
        "canonical_support": canonical_support,
        "retrieved_support": pool_support,
        "selected_support": selected_support,
        "recall_experiment": _recall_experiment(),
        "pool_support": pool_support,
        "measurement_status": {
            "retrieval": "measured",
            "generation": "prompt_only",
            "prompt_build": "measured",
            "validation": "measured",
        },
    }


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object in {path}")
    return payload


def _validate_fixture(fixture: dict[str, Any]) -> None:
    if int(fixture.get("evaluation_schema_version") or 0) != 1:
        raise ValueError("Unsupported evaluation_schema_version")
    scenarios = list(fixture.get("scenarios") or [])
    scenario_ids = [str(item.get("scenario_id") or "") for item in scenarios]
    if not scenarios or any(not value for value in scenario_ids) or len(set(scenario_ids)) != len(scenario_ids):
        raise ValueError("Fixture scenarios need unique scenario_id values")
    required_fields = {
        "purpose",
        "profile_ref",
        "job_context_ref",
        "expected_support_ref",
        "validation_case_ids",
    }
    for scenario in scenarios:
        missing = sorted(required_fields - set(scenario))
        if missing:
            raise ValueError(
                f"Scenario {scenario.get('scenario_id')!r} missing fields: {', '.join(missing)}"
            )
    validation_cases = list(fixture.get("validation_cases") or [])
    case_ids = {str(case.get("case_id") or "") for case in validation_cases}
    if any(not case_id for case_id in case_ids) or len(case_ids) != len(validation_cases):
        raise ValueError("Fixture validation cases need unique case_id values")
    for case in validation_cases:
        if "expected_valid" not in case or "expected_violation_class" not in case:
            raise ValueError(f"Validation case {case.get('case_id')!r} lacks expected outcome")


def _load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object in {path}")
    return payload


def _runtime_config(base_config: dict[str, Any], arm: str, pool_size: int) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    config.setdefault("pipeline", {}).setdefault("evidence_top_k", 2)
    config.setdefault("ranking_policy", {}).setdefault(
        "fit_label_thresholds", {"strong": 0.7, "stretch": 0.4}
    )
    semantic_alignment = config.setdefault("cv_analysis", {}).setdefault("semantic_alignment", {})
    semantic_alignment["enabled"] = arm == "current-hash"
    semantic_alignment["channel_pool_size"] = int(pool_size)
    return config


def _analysis_bundle(analysis_record: dict[str, Any]) -> dict[str, Any]:
    summary = dict(analysis_record.get("evidence_selection_summary") or {})
    return {
        "analysis_record": analysis_record,
        "selected_evidence": list(analysis_record.get("evidence_payload") or []),
        "selected_evidence_ids": list(summary.get("selected_evidence_ids") or []),
        "requirement_support": dict(summary.get("requirement_support") or {}),
        "evidence_selection_summary": summary,
        "semantic_alignment": dict(summary.get("semantic_alignment") or {}),
        "channel_counts": dict(summary.get("channel_counts") or {}),
        "merged_pool_size": int(summary.get("merged_pool_size") or 0),
        "deduped_pool_size": int(summary.get("deduped_pool_size") or 0),
    }


def _timed_retrieve(
    profile: dict[str, Any],
    job_context: dict[str, Any],
    config: dict[str, Any],
    top_k: int,
) -> tuple[dict[str, Any], dict[str, float]]:
    timings = {"retrieval_ms": 0.0, "selection_ms": 0.0}
    original_channel_selector = evidence_module._select_channel_candidates
    original_selection_run = evidence_module._EvidenceSelectionEngine.run

    def timed_channel_selector(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        started = time.perf_counter()
        try:
            return cast(list[dict[str, Any]], original_channel_selector(*args, **kwargs))
        finally:
            timings["retrieval_ms"] += (time.perf_counter() - started) * 1000

    def timed_selection_run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            return cast(dict[str, Any], original_selection_run(*args, **kwargs))
        finally:
            timings["selection_ms"] += (time.perf_counter() - started) * 1000

    setattr(evidence_module, "_select_channel_candidates", timed_channel_selector)
    setattr(evidence_module._EvidenceSelectionEngine, "run", timed_selection_run)
    started = time.perf_counter()
    try:
        bundle = retrieve_evidence_bundle(profile, job_context, top_k, config=config)
    finally:
        timings["total_ms"] = (time.perf_counter() - started) * 1000
        setattr(evidence_module, "_select_channel_candidates", original_channel_selector)
        setattr(evidence_module._EvidenceSelectionEngine, "run", original_selection_run)
    return bundle, timings


def _timed_analyze(
    profile: dict[str, Any],
    job_context: dict[str, Any],
    config: dict[str, Any],
    top_k: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, float]]:
    timings = {"retrieval_ms": 0.0, "selection_ms": 0.0}
    original_channel_selector = evidence_module._select_channel_candidates
    original_selection_run = evidence_module._EvidenceSelectionEngine.run

    def timed_channel_selector(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        started = time.perf_counter()
        try:
            return cast(list[dict[str, Any]], original_channel_selector(*args, **kwargs))
        finally:
            timings["retrieval_ms"] += (time.perf_counter() - started) * 1000

    def timed_selection_run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            return cast(dict[str, Any], original_selection_run(*args, **kwargs))
        finally:
            timings["selection_ms"] += (time.perf_counter() - started) * 1000

    setattr(evidence_module, "_select_channel_candidates", timed_channel_selector)
    setattr(evidence_module._EvidenceSelectionEngine, "run", timed_selection_run)
    started = time.perf_counter()
    try:
        analysis_record = dict(analyze_ranked_job(profile=profile, job=job_context, config=config, top_k=top_k))
    finally:
        timings["total_ms"] = (time.perf_counter() - started) * 1000
        setattr(evidence_module, "_select_channel_candidates", original_channel_selector)
        setattr(evidence_module._EvidenceSelectionEngine, "run", original_selection_run)
    return _analysis_bundle(analysis_record), analysis_record, timings


def _support_metrics(
    bundle: dict[str, Any],
    expected_support: dict[str, list[str]],
) -> dict[str, Any]:
    support = dict(bundle.get("requirement_support") or {})
    canonical = {key: set(value or []) for key, value in dict(support.get("canonical") or {}).items()}
    retrieved = {key: set(value or []) for key, value in dict(support.get("pool") or {}).items()}
    selected = {key: set(value or []) for key, value in dict(support.get("selected") or {}).items()}
    requirement_ids = sorted(set(expected_support) | set(canonical) | set(retrieved) | set(selected))
    expected_pairs = _support_pairs(expected_support)
    stage_pairs = {
        stage: _support_pairs(values)
        for stage, values in (("canonical", canonical), ("retrieved", retrieved), ("selected", selected))
    }
    canonical_to_retrieved = {
        key: sorted(canonical.get(key, set()) - retrieved.get(key, set()))
        for key in requirement_ids
    }
    retrieved_to_selected = {
        key: sorted(retrieved.get(key, set()) - selected.get(key, set()))
        for key in requirement_ids
    }
    expected_pair_errors = {
        key: sorted(
            selected.get(key, set())
            - set(expected_support.get(key) or [])
        )
        for key in requirement_ids
    }
    unexpected_selected = {
        key: sorted(selected.get(key, set()) - set(expected_support.get(key) or []))
        for key in requirement_ids
        if selected.get(key, set()) - set(expected_support.get(key) or [])
    }
    positive_requirements = {key for key, ids in expected_support.items() if ids}

    def requirement_recall(stage: str) -> float:
        if not positive_requirements:
            return 1.0
        valid_pairs = stage_pairs[stage] & expected_pairs
        covered = {
            requirement_id
            for requirement_id, evidence_id in valid_pairs
            if requirement_id in positive_requirements and evidence_id
        }
        return round(len(covered) / len(positive_requirements), 6)

    def pair_recall(stage: str) -> float:
        if not expected_pairs:
            return 1.0
        return round(len(stage_pairs[stage] & expected_pairs) / len(expected_pairs), 6)

    incorrect_pairs = sorted(stage_pairs["selected"] - expected_pairs)
    missed_pairs = sorted(expected_pairs - stage_pairs["selected"])
    direct_support_opportunities = {
        key: (
            []
            if set(expected_support.get(key) or []) & retrieved.get(key, set())
            else sorted(set(expected_support.get(key) or []) - retrieved.get(key, set()))
        )
        for key in sorted(positive_requirements)
    }
    selected_ids = [str(value) for value in list(bundle.get("selected_evidence_ids") or [])]
    duplicate_ids = sorted({value for value in selected_ids if selected_ids.count(value) > 1})
    return {
        "canonical_coverage": sum(bool(canonical.get(key)) for key in expected_support),
        "retrieved_coverage": sum(bool(retrieved.get(key)) for key in expected_support),
        "selected_coverage": sum(bool(selected.get(key)) for key in expected_support),
        "requirement_recall": {
            stage: requirement_recall(stage)
            for stage in ("canonical", "retrieved", "selected")
        },
        "evidence_pair_recall": {
            stage: pair_recall(stage)
            for stage in ("canonical", "retrieved", "selected")
        },
        "canonical_to_retrieved_loss": canonical_to_retrieved,
        "retrieved_to_selected_loss": retrieved_to_selected,
        "direct_support_opportunities": direct_support_opportunities,
        "expected_pair_errors": expected_pair_errors,
        "unexpected_selected": unexpected_selected,
        "incorrect_pairs": [list(pair) for pair in incorrect_pairs],
        "missed_pairs": [list(pair) for pair in missed_pairs],
        "assignment_precision": round(
            len(stage_pairs["selected"] & expected_pairs) / len(stage_pairs["selected"]), 6
        )
        if stage_pairs["selected"]
        else 1.0,
        "selected_ids": selected_ids,
        "duplicate_ids": duplicate_ids,
    }


def _run_validation(
    fixture: dict[str, Any],
    profile: dict[str, Any],
    bundle: dict[str, Any],
    *,
    requirement_coverage: list[dict[str, Any]] | None = None,
    validation_case: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], float]:
    validation = dict(fixture.get("validation") or {})
    case = dict(validation_case or {})
    config = copy.deepcopy(dict(validation.get("config") or {}))
    config.update(dict(case.get("config") or {}))
    selected_ids = list(bundle.get("selected_evidence_ids") or [])
    resolved_coverage = copy.deepcopy(list(requirement_coverage or []))
    if case.get("coverage_override") == "wrong_evidence_id":
        for row in resolved_coverage:
            if str(row.get("canonical_skill") or "") == "sql":
                row["selected_support"] = "verified"
                row["supporting_evidence_ids"] = ["ev_missing"]
    analysis_grounding: AnalysisGroundingPayload = {
        "requirement_coverage": resolved_coverage,
        "evidence_payload": list(bundle.get("selected_evidence") or []),
        "evidence_selection_summary": dict(
            bundle.get("evidence_selection_summary")
            or {"selected_evidence_ids": selected_ids}
        ),
    }
    started = time.perf_counter()
    result = run_all_validations(
        str(case.get("cv_text") or validation.get("cv_text") or ""),
        profile=profile,
        config=config,
        analysis_grounding=analysis_grounding,
    )
    return result, (time.perf_counter() - started) * 1000


def _fixture_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validation_class(result: dict[str, Any]) -> str:
    violations = [str(value) for value in list(result.get("grounding_violations") or [])]
    if any("Required skill" in violation for violation in violations):
        return "missing_verified_support"
    return "unrelated_validation" if not result.get("valid") else "none"


def run_benchmark(
    *,
    arm: str,
    pool_size: int,
    fixture_path: Path = DEFAULT_FIXTURE,
    policy_path: Path = DEFAULT_POLICY,
    runs: int = MEASURED_RUNS,
    warmups: int = WARMUP_RUNS,
) -> dict[str, Any]:
    if arm not in {"current-hash", "lexical"}:
        raise ValueError(f"Unsupported arm: {arm}")
    if runs <= 0 or warmups < 0:
        raise ValueError("runs must be positive and warmups cannot be negative")
    fixture = _load_json(fixture_path)
    _validate_fixture(fixture)
    base_config = _load_policy(policy_path)
    profile = dict(fixture.get("profile") or {})
    job_context = dict(fixture.get("job_context") or {})
    expected_support = {
        str(key): [str(value) for value in list(values or [])]
        for key, values in dict(fixture.get("expected_support") or {}).items()
    }
    config = _runtime_config(base_config, arm, pool_size)
    top_k = int(fixture.get("top_k") or 0)
    for _ in range(warmups):
        _timed_analyze(profile, job_context, config, top_k)

    samples: list[dict[str, Any]] = []
    final_bundle: dict[str, Any] | None = None
    final_analysis: dict[str, Any] | None = None
    final_validation_cases: list[dict[str, Any]] = []
    validation_cases = list(fixture.get("validation_cases") or [])
    if not validation_cases:
        validation_cases = [{"case_id": "default"}]
    for _ in range(runs):
        bundle, analysis_record, timings = _timed_analyze(profile, job_context, config, top_k)
        final_bundle = bundle
        final_analysis = analysis_record
        prompt_started = time.perf_counter()
        prompt = build_generation_prompt(
            jd=job_context,
            evidence=list(bundle.get("selected_evidence") or []),
            gap=dict(analysis_record.get("gap_summary") or {}),
            template=str(fixture.get("prompt_template") or "## Skills\n..."),
            profile=profile,
            config=config,
            evidence_selection_summary=dict(bundle.get("evidence_selection_summary") or {}),
        )
        prompt_build_ms = (time.perf_counter() - prompt_started) * 1000
        serialization_started = time.perf_counter()
        prompt_payload = json.dumps(
            {"job_context": job_context, "selected_evidence": bundle.get("selected_evidence") or []},
            sort_keys=True,
        )
        serialization_ms = (time.perf_counter() - serialization_started) * 1000
        case_results: list[dict[str, Any]] = []
        validation_ms = 0.0
        for case in validation_cases:
            validation, case_validation_ms = _run_validation(
                fixture,
                profile,
                bundle,
                requirement_coverage=list(analysis_record.get("requirement_coverage") or []),
                validation_case=case,
            )
            validation_ms += case_validation_ms
            actual_class = _validation_class(validation)
            case_results.append(
                {
                    "case_id": str(case.get("case_id") or ""),
                    "expected_valid": bool(case.get("expected_valid", True)),
                    "actual_valid": bool(validation.get("valid")),
                    "expected_violation_class": str(case.get("expected_violation_class") or "none"),
                    "actual_violation_class": actual_class,
                    "pass": bool(case.get("expected_valid", True)) == bool(validation.get("valid"))
                    and str(case.get("expected_violation_class") or "none") == actual_class,
                }
            )
        final_validation_cases = case_results
        samples.append(
            {
                **timings,
                "generation_prompt_build_ms": prompt_build_ms,
                "benchmark_payload_serialization_ms": serialization_ms,
                "validation_ms": validation_ms,
                "prompt_bytes": len(prompt.encode("utf-8")),
                "estimated_prompt_tokens": math.ceil(len(prompt.encode("utf-8")) / 4),
                "payload_bytes": len(prompt_payload.encode("utf-8")),
            }
        )

    assert final_bundle is not None and final_analysis is not None
    metric = _support_metrics(final_bundle, expected_support)
    pool_12_trigger_ids = sorted(
        key
        for key, values in metric["direct_support_opportunities"].items()
        if values
    )
    return {
        "arm": arm,
        "evaluation_schema_version": 1,
        "implementation_ref": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip(),
        "fixture_sha256": _fixture_sha256(fixture_path),
        "semantic_alignment_enabled": arm == "current-hash",
        "pool_size": pool_size,
        "top_k": top_k,
        "backend": final_bundle.get("semantic_alignment", {}).get("embedding_backend"),
        "requirement_support": metric,
        "pool_12_decision": {
            "status": "run_required" if pool_12_trigger_ids else "skipped",
            "trigger_requirement_ids": pool_12_trigger_ids,
            "reason": (
                "pool 8 or smaller arm has approved support absent from retrieved pool"
                if pool_12_trigger_ids
                else "no approved-support requirement is missing from retrieved pool"
            ),
        },
        "channel_counts": final_bundle.get("channel_counts"),
        "merged_pool_size": final_bundle.get("merged_pool_size"),
        "deduped_pool_size": final_bundle.get("deduped_pool_size"),
        "timing_ms": {
            key: {
                "median": statistics.median(sample[key] for sample in samples),
                "p95": _percentile([sample[key] for sample in samples], 0.95),
            }
            for key in (
                "retrieval_ms",
                "selection_ms",
                "total_ms",
                "generation_prompt_build_ms",
                "benchmark_payload_serialization_ms",
                "validation_ms",
            )
        },
        "context": {
            "prompt_bytes": max(sample["prompt_bytes"] for sample in samples),
            "estimated_prompt_tokens": max(sample["estimated_prompt_tokens"] for sample in samples),
            "payload_bytes": max(sample["payload_bytes"] for sample in samples),
        },
        "validation": {
            "case_results": final_validation_cases,
            "passed_cases": sum(bool(case["pass"]) for case in final_validation_cases),
            "case_count": len(final_validation_cases),
        },
        "fixture": str(fixture_path.relative_to(REPO_ROOT)),
        "warmup_runs": warmups,
        "measured_runs": runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weight", type=float)
    parser.add_argument("--arm", choices=("current-hash", "lexical"))
    parser.add_argument("--pool-size", type=int)
    parser.add_argument("--runs", type=int, default=MEASURED_RUNS)
    parser.add_argument("--warmups", type=int, default=WARMUP_RUNS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.weight is not None:
        result = run(args.weight)
    elif args.arm is not None and args.pool_size is not None:
        result = run_benchmark(
            arm=args.arm,
            pool_size=args.pool_size,
            runs=args.runs,
            warmups=args.warmups,
        )
    else:
        parser.error("provide --weight or both --arm and --pool-size")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
