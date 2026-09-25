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
    profiles = fixture.get("profiles")
    job_contexts = fixture.get("job_contexts")
    expected_support_maps = fixture.get("expected_support_maps")
    if not isinstance(profiles, dict) or not isinstance(job_contexts, dict) or not isinstance(expected_support_maps, dict):
        raise ValueError("Fixture needs profiles, job_contexts, and expected_support_maps registries")
    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id") or "")
        for field, registry in (
            ("profile_ref", profiles),
            ("job_context_ref", job_contexts),
            ("expected_support_ref", expected_support_maps),
        ):
            reference = str(scenario.get(field) or "")
            if not reference or reference not in registry:
                raise ValueError(f"Scenario {scenario_id!r} has missing {field}: {reference!r}")
        validation_ids = list(scenario.get("validation_case_ids") or [])
        if not validation_ids:
            raise ValueError(f"Scenario {scenario_id!r} needs validation_case_ids")
    for field in ("profile_ref", "job_context_ref", "expected_support_ref"):
        references = [str(scenario.get(field) or "") for scenario in scenarios]
        if len(set(references)) != len(references):
            raise ValueError(f"Scenario {field} values must be unique")
    validation_cases = list(fixture.get("validation_cases") or [])
    case_ids = {str(case.get("case_id") or "") for case in validation_cases}
    if any(not case_id for case_id in case_ids) or len(case_ids) != len(validation_cases):
        raise ValueError("Fixture validation cases need unique case_id values")
    for case in validation_cases:
        if "expected_valid" not in case or "expected_violation_class" not in case:
            raise ValueError(f"Validation case {case.get('case_id')!r} lacks expected outcome")
    missing_case_refs = sorted(
        {
            str(case_id)
            for scenario in scenarios
            for case_id in list(scenario.get("validation_case_ids") or [])
            if str(case_id) not in case_ids
        }
    )
    if missing_case_refs:
        raise ValueError(f"Fixture scenarios reference missing validation cases: {', '.join(missing_case_refs)}")


def _resolve_scenarios(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    _validate_fixture(fixture)
    profiles = dict(fixture["profiles"])
    job_contexts = dict(fixture["job_contexts"])
    expected_support_maps = dict(fixture["expected_support_maps"])
    validation_cases = {
        str(case["case_id"]): case
        for case in list(fixture.get("validation_cases") or [])
    }
    resolved: list[dict[str, Any]] = []
    for scenario in list(fixture.get("scenarios") or []):
        validation_case_ids = [str(value) for value in list(scenario.get("validation_case_ids") or [])]
        resolved.append(
            {
                "scenario_id": str(scenario["scenario_id"]),
                "purpose": str(scenario.get("purpose") or ""),
                "profile": copy.deepcopy(profiles[str(scenario["profile_ref"])]),
                "job_context": copy.deepcopy(job_contexts[str(scenario["job_context_ref"])]),
                "expected_support": {
                    str(key): [str(value) for value in list(values or [])]
                    for key, values in dict(expected_support_maps[str(scenario["expected_support_ref"])]).items()
                },
                "evidence_budget": int(scenario.get("evidence_budget") or fixture.get("top_k") or 0),
                "top_k": int(scenario.get("top_k") or fixture.get("top_k") or 0),
                "validation_cases": [copy.deepcopy(validation_cases[case_id]) for case_id in validation_case_ids],
            }
        )
    return resolved


def _load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object in {path}")
    return payload


def _runtime_config(base_config: dict[str, Any], arm: str, pool_size: int) -> dict[str, Any]:
    normalized_arm = "lexical-requirement-aware" if arm == "lexical" else arm
    if normalized_arm not in {
        "lexical-baseline",
        "lexical-ablation",
        "lexical-requirement-aware",
        "current-hash",
    }:
        raise ValueError(f"Unsupported arm: {arm}")
    config = copy.deepcopy(base_config)
    config.setdefault("pipeline", {}).setdefault("evidence_top_k", 2)
    config.setdefault("ranking_policy", {}).setdefault(
        "fit_label_thresholds", {"strong": 0.7, "stretch": 0.4}
    )
    semantic_alignment = config.setdefault("cv_analysis", {}).setdefault("semantic_alignment", {})
    semantic_alignment["enabled"] = normalized_arm == "current-hash"
    semantic_alignment["channel_pool_size"] = int(pool_size)
    selection_policy = config["cv_analysis"].setdefault("selection_policy", {})
    if normalized_arm == "lexical-baseline":
        selection_policy.update(
            {
                "multi_channel_bonus": 0.0,
                "type_weight_factor": 0.0,
                "residual_score_factor": 0.0,
                "new_type_bonus": 0.0,
                "same_type_penalty": 0.0,
                "requirement_gain_weight": 0.0,
            }
        )
    elif normalized_arm == "lexical-ablation":
        selection_policy["requirement_gain_weight"] = 0.0
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
    *,
    explicit_requirement_links: bool = True,
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
            return "not_applicable"
        valid_pairs = stage_pairs[stage] & expected_pairs
        covered = {
            requirement_id
            for requirement_id, evidence_id in valid_pairs
            if requirement_id in positive_requirements and evidence_id
        }
        return round(len(covered) / len(positive_requirements), 6)

    def pair_recall(stage: str) -> float:
        if not expected_pairs:
            return "not_applicable"
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
        "requirement_counts": {
            stage: {
                "covered": sum(
                    1
                    for requirement_id, evidence_id in stage_pairs[stage] & expected_pairs
                    if requirement_id in positive_requirements and evidence_id
                ),
                "denominator": len(positive_requirements),
            }
            for stage in ("canonical", "retrieved", "selected")
        },
        "evidence_pair_recall": {
            stage: pair_recall(stage)
            for stage in ("canonical", "retrieved", "selected")
        },
        "evidence_pair_counts": {
            stage: {
                "covered": len(stage_pairs[stage] & expected_pairs),
                "denominator": len(expected_pairs),
            }
            for stage in ("canonical", "retrieved", "selected")
        },
        "canonical_to_retrieved_loss": canonical_to_retrieved,
        "retrieved_to_selected_loss": retrieved_to_selected,
        "direct_support_opportunities": direct_support_opportunities,
        "expected_pair_errors": expected_pair_errors,
        "unexpected_selected": unexpected_selected,
        "incorrect_pairs": [list(pair) for pair in incorrect_pairs],
        "correct_pairs": [list(pair) for pair in sorted(stage_pairs["selected"] & expected_pairs)],
        "missed_pairs": [list(pair) for pair in missed_pairs],
        "assignment_precision": (
            round(len(stage_pairs["selected"] & expected_pairs) / len(stage_pairs["selected"]), 6)
            if stage_pairs["selected"]
            else 1.0
        ) if explicit_requirement_links else "not_applicable",
        "explicit_requirement_links": explicit_requirement_links,
        "selected_link_count": len(stage_pairs["selected"]),
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


def _timing_summary(samples: list[dict[str, float]], key: str) -> dict[str, float]:
    values = [float(sample[key]) for sample in samples]
    return {
        "median": statistics.median(values),
        "p95": _percentile(values, 0.95),
    }


def _scenario_profile_for_analysis(profile: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    prepared = copy.deepcopy(profile)
    projected_pool = list(prepared.pop("_projected_evidence_pool", []) or [])
    prepared.setdefault("name", f"Benchmark Candidate {scenario_id}")
    document_id = f"benchmark-{scenario_id}"
    prepared.setdefault(
        "source_documents",
        [{
            "id": document_id,
            "filename": f"{scenario_id}.json",
            "media_type": "application/json",
            "sha256": "0" * 64,
            "origin": "uploaded",
        }],
    )
    for field in (
        "experiences",
        "education",
        "projects",
        "achievements",
        "certifications",
        "volunteering",
        "languages",
        "skills",
        "role_families",
        "domain_tags",
        "responsibility_themes",
    ):
        prepared.setdefault(field, [])
    if projected_pool:
        evidence_ids_by_skill: dict[str, list[str]] = {}
        for item in projected_pool:
            evidence_id = str(item.get("evidence_id") or "")
            for skill in list(item.get("skills") or []):
                skill_name = str(skill)
                evidence_ids_by_skill.setdefault(skill_name, []).append(evidence_id)
        prepared["skills"] = [
            {
                "id": f"{scenario_id}-{skill.casefold().replace(' ', '-')}",
                "name": skill,
                "origin": "extracted_explicit",
                "confidence": 1.0,
                "support_status": "supported",
                "evidence_refs": sorted(set(evidence_ids)),
            }
            for skill, evidence_ids in sorted(evidence_ids_by_skill.items())
        ]
        prepared["experiences"] = [
            {
                "id": f"{scenario_id}-experience",
                "role": "Benchmark Engineer",
                "company": "Benchmark Fixture",
                "source_refs": [{"document_id": document_id}],
                "evidence": [
                    {
                        "id": str(item.get("evidence_id") or ""),
                        "kind": "work_achievement",
                        "text": str(item.get("text") or item.get("business_value") or ""),
                        "source_refs": [{"document_id": document_id}],
                    }
                    for item in projected_pool
                ],
            }
        ]
    return prepared


def _run_benchmark_scenario(
    *,
    fixture: dict[str, Any],
    scenario: dict[str, Any],
    arm: str,
    pool_size: int,
    base_config: dict[str, Any],
    runs: int,
    warmups: int,
) -> dict[str, Any]:
    profile = _scenario_profile_for_analysis(scenario["profile"], str(scenario["scenario_id"]))
    job_context = dict(scenario["job_context"])
    job_context.setdefault("baseline_fit", 0.8)
    job_context.setdefault("baseline_fit_label", "strong")
    config = _runtime_config(base_config, arm, pool_size)
    top_k = int(scenario["top_k"])
    for _ in range(warmups):
        _timed_analyze(profile, job_context, config, top_k)

    samples: list[dict[str, Any]] = []
    final_bundle: dict[str, Any] | None = None
    final_analysis: dict[str, Any] | None = None
    final_validation_cases: list[dict[str, Any]] = []
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
        for case in list(scenario["validation_cases"]):
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
                "selected_item_count": len(list(bundle.get("selected_evidence") or [])),
            }
        )

    assert final_bundle is not None and final_analysis is not None
    explicit_links = arm != "lexical-baseline"
    metric = _support_metrics(
        final_bundle,
        scenario["expected_support"],
        explicit_requirement_links=explicit_links,
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "purpose": scenario["purpose"],
        "evidence_budget": scenario["evidence_budget"],
        "top_k": top_k,
        "metrics": metric,
        "timing_ms": {
            key: _timing_summary(samples, key)
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
            "selected_item_count": max(sample["selected_item_count"] for sample in samples),
            "prompt_bytes": max(sample["prompt_bytes"] for sample in samples),
            "estimated_prompt_tokens": max(sample["estimated_prompt_tokens"] for sample in samples),
            "payload_bytes": max(sample["payload_bytes"] for sample in samples),
        },
        "validation": {
            "case_results": final_validation_cases,
            "passed_cases": sum(bool(case["pass"]) for case in final_validation_cases),
            "case_count": len(final_validation_cases),
        },
        "backend": final_bundle.get("semantic_alignment", {}).get("embedding_backend"),
        "selection_policy": dict(final_bundle.get("evidence_selection_summary", {}).get("selection_policy") or {}),
    }


def _aggregate_scenario_metrics(scenario_results: list[dict[str, Any]]) -> dict[str, Any]:
    stages = ("canonical", "retrieved", "selected")
    requirement_counts = {
        stage: {
            "covered": sum(int(result["metrics"]["requirement_counts"][stage]["covered"]) for result in scenario_results),
            "denominator": sum(int(result["metrics"]["requirement_counts"][stage]["denominator"]) for result in scenario_results),
        }
        for stage in stages
    }
    pair_counts = {
        stage: {
            "covered": sum(int(result["metrics"]["evidence_pair_counts"][stage]["covered"]) for result in scenario_results),
            "denominator": sum(int(result["metrics"]["evidence_pair_counts"][stage]["denominator"]) for result in scenario_results),
        }
        for stage in stages
    }

    def ratio(counts: dict[str, int]) -> float | str:
        return round(counts["covered"] / counts["denominator"], 6) if counts["denominator"] else "not_applicable"

    def macro(metric_key: str, stage: str) -> float | str:
        values = [
            result["metrics"][metric_key][stage]
            for result in scenario_results
            if isinstance(result["metrics"][metric_key][stage], (int, float))
        ]
        return round(statistics.mean(values), 6) if values else "not_applicable"

    return {
        "requirement_recall": {stage: ratio(requirement_counts[stage]) for stage in stages},
        "evidence_pair_recall": {stage: ratio(pair_counts[stage]) for stage in stages},
        "micro_coverage": {
            "requirement_recall": {stage: ratio(requirement_counts[stage]) for stage in stages},
            "evidence_pair_recall": {stage: ratio(pair_counts[stage]) for stage in stages},
        },
        "macro_coverage": {
            "requirement_recall": {stage: macro("requirement_recall", stage) for stage in stages},
            "evidence_pair_recall": {stage: macro("evidence_pair_recall", stage) for stage in stages},
        },
        "requirement_counts": requirement_counts,
        "evidence_pair_counts": pair_counts,
        "canonical_coverage": sum(result["metrics"]["canonical_coverage"] for result in scenario_results),
        "retrieved_coverage": sum(result["metrics"]["retrieved_coverage"] for result in scenario_results),
        "selected_coverage": sum(result["metrics"]["selected_coverage"] for result in scenario_results),
        "incorrect_pairs": [
            [result["scenario_id"], *pair]
            for result in scenario_results
            for pair in result["metrics"].get("incorrect_pairs", [])
        ],
        "missed_pairs": [
            [result["scenario_id"], *pair]
            for result in scenario_results
            for pair in result["metrics"].get("missed_pairs", [])
        ],
        "assignment_precision": (
            "not_applicable"
            if not all(result["metrics"].get("explicit_requirement_links") for result in scenario_results)
            else round(
                sum(
                    len(set(map(tuple, result["metrics"].get("correct_pairs", []))))
                    for result in scenario_results
                )
                / max(
                    sum(int(result["metrics"].get("selected_link_count") or 0) for result in scenario_results),
                    1,
                ),
                6,
            )
        ),
        "explicit_requirement_links": all(
            bool(result["metrics"].get("explicit_requirement_links")) for result in scenario_results
        ),
        "direct_support_opportunities": {
            requirement_id: sorted(
                {
                    evidence_id
                    for result in scenario_results
                    for evidence_id in result["metrics"].get("direct_support_opportunities", {}).get(requirement_id, [])
                }
            )
            for requirement_id in sorted(
                {
                    requirement_id
                    for result in scenario_results
                    for requirement_id in result["metrics"].get("direct_support_opportunities", {})
                }
            )
        },
        "selected_ids": sorted(
            {
                evidence_id
                for result in scenario_results
                for evidence_id in result["metrics"].get("selected_ids", [])
            }
        ),
    }


def run_benchmark(
    *,
    arm: str,
    pool_size: int = 4,
    fixture_path: Path = DEFAULT_FIXTURE,
    policy_path: Path = DEFAULT_POLICY,
    runs: int = MEASURED_RUNS,
    warmups: int = WARMUP_RUNS,
) -> dict[str, Any]:
    if arm not in {"current-hash", "lexical", "lexical-baseline", "lexical-ablation", "lexical-requirement-aware"}:
        raise ValueError(f"Unsupported arm: {arm}")
    if runs <= 0 or warmups < 0:
        raise ValueError("runs must be positive and warmups cannot be negative")
    fixture = _load_json(fixture_path)
    scenarios = _resolve_scenarios(fixture)
    base_config = _load_policy(policy_path)
    scenario_results = [
        _run_benchmark_scenario(
            fixture=fixture,
            scenario=scenario,
            arm=arm,
            pool_size=pool_size,
            base_config=base_config,
            runs=runs,
            warmups=warmups,
        )
        for scenario in scenarios
    ]
    aggregate = _aggregate_scenario_metrics(scenario_results)
    timing_keys = tuple(scenario_results[0]["timing_ms"])
    return {
        "arm": "lexical-requirement-aware" if arm == "lexical" else arm,
        "evaluation_schema_version": int(fixture["evaluation_schema_version"]),
        "implementation_ref": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip(),
        "fixture_sha256": _fixture_sha256(fixture_path),
        "scenario_set": [result["scenario_id"] for result in scenario_results],
        "scenario_count": len(scenario_results),
        "workload_count": len(scenario_results),
        "semantic_alignment_enabled": arm == "current-hash",
        "pool_size": pool_size,
        "top_k": sorted({result["top_k"] for result in scenario_results}),
        "evidence_budgets": sorted({result["evidence_budget"] for result in scenario_results}),
        "backend": scenario_results[-1]["backend"],
        "requirement_support": aggregate,
        "scenarios": scenario_results,
        "timing_ms": {
            key: {
                "median": statistics.median(result["timing_ms"][key]["median"] for result in scenario_results),
                "p95": max(result["timing_ms"][key]["p95"] for result in scenario_results),
            }
            for key in timing_keys
        },
        "context": {
            "selected_item_count": max(result["context"]["selected_item_count"] for result in scenario_results),
            "prompt_bytes": max(result["context"]["prompt_bytes"] for result in scenario_results),
            "estimated_prompt_tokens": max(result["context"]["estimated_prompt_tokens"] for result in scenario_results),
            "payload_bytes": max(result["context"]["payload_bytes"] for result in scenario_results),
        },
        "validation": {
            "passed_cases": sum(result["validation"]["passed_cases"] for result in scenario_results),
            "case_count": sum(result["validation"]["case_count"] for result in scenario_results),
            "scenario_results": [
                {
                    "scenario_id": result["scenario_id"],
                    "passed_cases": result["validation"]["passed_cases"],
                    "case_count": result["validation"]["case_count"],
                }
                for result in scenario_results
            ],
        },
        "arm_configuration": {
            "retrieval": "hash" if arm == "current-hash" else "lexical",
            "selection": arm,
            "provider_calls": False,
        },
        "fixture": str(fixture_path.relative_to(REPO_ROOT)),
        "warmup_runs": warmups,
        "measured_runs": runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weight", type=float)
    parser.add_argument(
        "--arm",
        choices=("current-hash", "lexical", "lexical-baseline", "lexical-ablation", "lexical-requirement-aware"),
    )
    parser.add_argument("--pool-size", type=int, default=4)
    parser.add_argument("--runs", type=int, default=MEASURED_RUNS)
    parser.add_argument("--warmups", type=int, default=WARMUP_RUNS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.weight is not None:
        result = run(args.weight)
    elif args.arm is not None:
        result = run_benchmark(
            arm=args.arm,
            pool_size=args.pool_size,
            runs=args.runs,
            warmups=args.warmups,
        )
    else:
        parser.error("provide --weight or --arm")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
