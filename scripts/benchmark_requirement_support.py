"""Benchmark requirement-specific evidence support without external services."""

from __future__ import annotations

import argparse
import copy
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


def _load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object in {path}")
    return payload


def _runtime_config(base_config: dict[str, Any], arm: str, pool_size: int) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    semantic_alignment = config.setdefault("cv_analysis", {}).setdefault("semantic_alignment", {})
    semantic_alignment["enabled"] = arm == "current-hash"
    semantic_alignment["channel_pool_size"] = int(pool_size)
    return config


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


def _support_metrics(
    bundle: dict[str, Any],
    expected_support: dict[str, list[str]],
) -> dict[str, Any]:
    support = dict(bundle.get("requirement_support") or {})
    canonical = {key: set(value or []) for key, value in dict(support.get("canonical") or {}).items()}
    retrieved = {key: set(value or []) for key, value in dict(support.get("pool") or {}).items()}
    selected = {key: set(value or []) for key, value in dict(support.get("selected") or {}).items()}
    canonical_to_retrieved = {
        key: sorted(canonical.get(key, set()) - retrieved.get(key, set()))
        for key in expected_support
    }
    retrieved_to_selected = {
        key: sorted(retrieved.get(key, set()) - selected.get(key, set()))
        for key in expected_support
    }
    expected_pair_errors = {
        key: sorted(
            selected.get(key, set())
            - set(expected_support.get(key) or [])
        )
        for key in expected_support
    }
    unexpected_selected = {
        key: sorted(
            selected.get(key, set())
            - set(expected_support.get(key) or [])
        )
        for key in expected_support
    }
    selected_ids = [str(value) for value in list(bundle.get("selected_evidence_ids") or [])]
    duplicate_ids = sorted({value for value in selected_ids if selected_ids.count(value) > 1})
    return {
        "canonical_coverage": sum(bool(canonical.get(key)) for key in expected_support),
        "retrieved_coverage": sum(bool(retrieved.get(key)) for key in expected_support),
        "selected_coverage": sum(bool(selected.get(key)) for key in expected_support),
        "canonical_to_retrieved_loss": canonical_to_retrieved,
        "retrieved_to_selected_loss": retrieved_to_selected,
        "direct_support_opportunities": canonical_to_retrieved,
        "expected_pair_errors": expected_pair_errors,
        "unexpected_selected": unexpected_selected,
        "selected_ids": selected_ids,
        "duplicate_ids": duplicate_ids,
    }


def _run_validation(
    fixture: dict[str, Any],
    profile: dict[str, Any],
    bundle: dict[str, Any],
) -> tuple[dict[str, Any], float]:
    validation = dict(fixture.get("validation") or {})
    config = dict(validation.get("config") or {})
    analysis_grounding: AnalysisGroundingPayload = {
        "requirement_coverage": [
            {
                "requirement": requirement_id,
                "support_strength": "supported" if ids else "unsupported",
                "evidence_support_count": len(ids),
            }
            for requirement_id, ids in dict(bundle.get("requirement_support", {}).get("selected") or {}).items()
        ],
        "evidence_payload": list(bundle.get("selected_evidence") or []),
        "evidence_selection_summary": {
            "selected_evidence_ids": list(bundle.get("selected_evidence_ids") or [])
        },
    }
    started = time.perf_counter()
    result = run_all_validations(
        str(validation.get("cv_text") or ""),
        profile=profile,
        config=config,
        analysis_grounding=analysis_grounding,
    )
    return result, (time.perf_counter() - started) * 1000


def run_benchmark(
    *,
    arm: str,
    pool_size: int,
    fixture_path: Path = DEFAULT_FIXTURE,
    policy_path: Path = DEFAULT_POLICY,
) -> dict[str, Any]:
    if arm not in {"current-hash", "lexical"}:
        raise ValueError(f"Unsupported arm: {arm}")
    fixture = _load_json(fixture_path)
    base_config = _load_policy(policy_path)
    profile = dict(fixture.get("profile") or {})
    job_context = dict(fixture.get("job_context") or {})
    expected_support = {
        str(key): [str(value) for value in list(values or [])]
        for key, values in dict(fixture.get("expected_support") or {}).items()
    }
    config = _runtime_config(base_config, arm, pool_size)
    top_k = int(fixture.get("top_k") or 0)
    for _ in range(WARMUP_RUNS):
        _timed_retrieve(profile, job_context, config, top_k)

    samples: list[dict[str, Any]] = []
    final_bundle: dict[str, Any] | None = None
    for _ in range(MEASURED_RUNS):
        bundle, timings = _timed_retrieve(profile, job_context, config, top_k)
        final_bundle = bundle
        prompt_started = time.perf_counter()
        prompt_payload = json.dumps(
            {"job_context": job_context, "selected_evidence": bundle.get("selected_evidence") or []},
            sort_keys=True,
        )
        prompt_ms = (time.perf_counter() - prompt_started) * 1000
        validation, validation_ms = _run_validation(fixture, profile, bundle)
        samples.append(
            {
                **timings,
                "prompt_ms": prompt_ms,
                "validation_ms": validation_ms,
                "context_chars": len(prompt_payload),
                "estimated_context_tokens": math.ceil(len(prompt_payload) / 4),
                "validation_valid": bool(validation.get("valid")),
            }
        )

    assert final_bundle is not None
    metric = _support_metrics(final_bundle, expected_support)
    pool_12_trigger_ids = sorted(
        key
        for key, values in metric["direct_support_opportunities"].items()
        if values
    )
    return {
        "arm": arm,
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
            for key in ("retrieval_ms", "selection_ms", "total_ms", "prompt_ms", "validation_ms")
        },
        "context": {
            "chars": max(sample["context_chars"] for sample in samples),
            "estimated_tokens": max(sample["estimated_context_tokens"] for sample in samples),
        },
        "validation": {
            "valid_runs": sum(sample["validation_valid"] for sample in samples),
            "runs": len(samples),
        },
        "fixture": str(fixture_path.relative_to(REPO_ROOT)),
        "warmup_runs": WARMUP_RUNS,
        "measured_runs": MEASURED_RUNS,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weight", type=float)
    parser.add_argument("--arm", choices=("current-hash", "lexical"))
    parser.add_argument("--pool-size", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.weight is not None:
        result = run(args.weight)
    elif args.arm is not None and args.pool_size is not None:
        result = run_benchmark(arm=args.arm, pool_size=args.pool_size)
    else:
        parser.error("provide --weight or both --arm and --pool-size")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
