import json
import os
from pathlib import Path

import pytest

from scripts.prepare_rag_impact_corpus import (
    prepare_corpus,
    sanitize_job,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "linkedin-2026-09-25-22-54-17.json"
BASE = ROOT / "tests" / "fixtures" / "rag_impact_benchmark.json"
SOURCE = Path(os.environ.get("FITCV_RAG_SOURCE", SOURCE))
source_required = pytest.mark.skipif(
    not SOURCE.exists(),
    reason="task-local raw job source is not tracked; run with FITCV_RAG_SOURCE for source proof",
)


@source_required
def test_source_hash_and_sanitization_are_stable() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    job = sanitize_job(source[0])

    assert len(source) == 100
    assert sha256_file(SOURCE) == prepare_corpus(SOURCE, BASE, 20260925)["source_sha256"]
    assert set(job) == {
        "job_id", "title", "description", "location", "company_name",
        "work_mode", "contract_type", "experience_level", "job_function",
    }
    assert not any(key.lower().endswith("url") for key in job)
    assert "@" not in job["description"]
    assert "http" not in job["description"].lower()
    assert "http" not in job["title"].lower()
    assert "@" not in job["company_name"]


@source_required
def test_prepare_corpus_has_exact_splits_and_pair_metadata() -> None:
    corpus = prepare_corpus(SOURCE, BASE, 20260925)
    jobs = corpus["jobs"]

    assert {name: len(items) for name, items in jobs.items()} == {
        "development": 10,
        "pilot": 10,
        "held_out": 20,
    }
    cases = [case for items in jobs.values() for case in items]
    assert len({case["scenario_id"] for case in cases}) == 40
    assert len({case["source_job_id"] for case in cases}) == 40
    assert sum(case["context_difference"]["fitcv_uses_less_evidence"] for case in cases) >= 10
    assert all(case["requirements"] for case in cases)
    assert all(case["difficulty"] in {"easy", "medium", "hard"} for case in cases)

