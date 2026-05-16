"""
@meta
type: test
scope: unit
domain: structural_contracts
covers:
  - structural guardrails for shared contract ownership
tags:
  - fast
  - ci-safe
"""

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_synonym_trace_builder_has_single_runtime_owner() -> None:
    root = _repo_root()
    worker_source = (root / "src/fitcv_cp/worker_job.py").read_text(encoding="utf-8")
    proposals_source = (root / "src/fitcv_cp/synonym_proposals.py").read_text(encoding="utf-8")

    assert "def _build_synonym_proposals_trace_payload" not in worker_source
    assert proposals_source.count("def _build_synonym_proposals_trace_payload") == 1


def test_targeted_modules_avoid_hardcoded_consolidated_schema_literals() -> None:
    root = _repo_root()
    target_files = [
        root / "src/fitcv/pipeline.py",
        root / "src/fitcv_cp/app.py",
        root / "src/fitcv_cp/worker_job.py",
        root / "src/fitcv_cp/synonym_proposals.py",
    ]
    forbidden_literals = {
        "stage_transition_artifacts_v6",
        "mapping_suggestions_v1",
        "mapping_suggestions_aggregate_v1",
        "synonym_proposals_v1",
        "synonym_proposals_queue_v1",
    }

    for target in target_files:
        source = target.read_text(encoding="utf-8")
        for literal in forbidden_literals:
            assert literal not in source, f"{target}: found forbidden schema literal {literal}"
