"""Compare requirement-aware evidence selection against baseline mode."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import time
from pathlib import Path

from fitcv.cv_generator import build_generation_prompt
from fitcv.evidence import (
    _annotate_requirement_support,
    build_required_skill_descriptors,
    retrieve_evidence_bundle,
)
from fitcv.validator import run_all_validations


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
    retrieval_latency_ms = round((time.perf_counter() - started) * 1000, 3)
    support = dict(bundle.get("requirement_support") or {})
    return {
        "channel_pool_size": channel_pool_size,
        "canonical_support": dict(support.get("canonical") or {}),
        "retrieved_support": dict(support.get("pool") or {}),
        "selected_support": dict(support.get("selected") or {}),
        "selected_evidence_ids": list(bundle.get("selected_evidence_ids") or []),
        "retrieval_latency_ms": retrieval_latency_ms,
        "selected_context_chars": sum(
            len(str(item.get("text") or ""))
            for item in list(bundle.get("selected_evidence") or [])
        ),
    }


def _annotation_cost_probe() -> dict[str, object]:
    items = [
        _item(f"ev-{letter}", ["Python"], "Python")
        for letter in ("a", "b", "c", "d", "e")
    ]
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
    retrieval_ms = round((time.perf_counter() - started) * 1000, 3)
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
    prompt_latency_ms = round((time.perf_counter() - prompt_started) * 1000, 3)
    validation_started = time.perf_counter()
    validation = run_all_validations(
        "## Skills\nSQL\n",
        {"skills": [{"name": "SQL"}], "experiences": [], "projects": []},
        {
            "required_cv_sections": ["Skills"],
            "cv_max_pages": 2,
            "cv": {"validation": {"allow_profile_skill_outside_selected_evidence": True}},
        },
        analysis_grounding={
            "evidence_payload": selected,
            "requirement_coverage": requirement_coverage,
        },
    )
    validation_latency_ms = round((time.perf_counter() - validation_started) * 1000, 3)
    selected_pairs = _support_pairs(selected_support)
    return {
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip(),
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
            "retrieval_latency_ms": retrieval_ms,
            "prompt_build_latency_ms": prompt_latency_ms,
            "validation_latency_ms": validation_latency_ms,
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weight", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.weight)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
