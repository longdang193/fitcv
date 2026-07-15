"""Tests for fitcv.ai_score — all pure unit tests (no cloud calls)."""

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from fitcv.ai_score import (
    build_ai_score_contract_fingerprint,
    build_scoring_prompt,
    parse_score_response,
)


# ── helpers ───────────────────────────────────────────────────────────────────

_VALID_RESPONSE = json.dumps({
    "ai_score": 0.85,
    "fit_label": "strong",
    "score_reasoning": "Candidate has SQL, Python, and BigQuery experience matching JD.",
    "matched_strengths": ["SQL", "Python", "BigQuery"],
    "key_risks": [],
})


def test_ranking_ai_prompt_v2_requests_score_without_fit_label() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
    )

    assert '"ai_score"' in prompt
    assert "fit_label" not in prompt
    assert "strong_threshold" not in prompt
    assert "stretch_threshold" not in prompt


def test_parse_score_response_keeps_legacy_label_diagnostic_only() -> None:
    result = parse_score_response(_VALID_RESPONSE)

    assert "fit_label" not in result
    assert result["legacy_model_fit_label"] == "strong"


def test_ai_score_contract_fingerprint_excludes_fit_thresholds() -> None:
    base = {
        "ai_score_model": "cx/test-model",
        "prompts": {"ranking": {"ai_score": {"prompt_id": "ranking.ai_score.v2"}}},
    }
    first = build_ai_score_contract_fingerprint(
        {**base, "fit_label_thresholds": {"strong": 0.7, "stretch": 0.4}}
    )
    second = build_ai_score_contract_fingerprint(
        {**base, "fit_label_thresholds": {"strong": 0.9, "stretch": 0.8}}
    )

    assert first == second
    assert "strong_threshold" not in first["payload"]
    assert "stretch_threshold" not in first["payload"]


# ── build_scoring_prompt ──────────────────────────────────────────────────────

def test_build_scoring_prompt_includes_jd_summary() -> None:
    prompt = build_scoring_prompt(
        jd_summary="Data Engineer role requiring SQL, Python",
        candidate_summary="3 years experience in SQL, Python, BigQuery",
        top_evidence=["Built GA4 pipeline reducing latency 40%"],
    )
    assert "Data Engineer" in prompt
    assert "SQL" in prompt


def test_build_scoring_prompt_includes_candidate_summary() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="3 years experience in SQL, Python, BigQuery",
        top_evidence=[],
    )
    assert "BigQuery" in prompt or "3 years" in prompt


def test_build_scoring_prompt_includes_score_in_rubric() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
    )
    assert "score" in prompt.lower()


def test_build_scoring_prompt_includes_rubric_range() -> None:
    """Rubric range 0.0-1.0 must appear in prompt."""
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
    )
    assert "0.0" in prompt or "1.0" in prompt


def test_build_scoring_prompt_excludes_fit_labels() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
    )
    assert "fit_label" not in prompt


def test_build_scoring_prompt_includes_top_evidence() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=["Built GA4 pipeline reducing latency 40%"],
    )
    assert "GA4" in prompt


def test_build_scoring_prompt_contains_required_skills_in_rubric() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="mid-level engineer",
        top_evidence=[],
    )
    assert "required-skill" in prompt.lower()


def test_build_scoring_prompt_makes_preferences_secondary() -> None:
    prompt = build_scoring_prompt(
        jd_summary="Analytics role",
        candidate_summary="candidate",
        top_evidence=[],
    )
    assert "secondary" in prompt.lower()
    assert "preferences" in prompt.lower()


def test_build_scoring_prompt_contains_seniority_in_rubric() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="mid-level engineer",
        top_evidence=[],
    )
    assert "seniority" in prompt.lower()


def test_build_scoring_prompt_specifies_json_output() -> None:
    """Prompt must tell model to return JSON only, no prose."""
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
    )
    assert "json" in prompt.lower()


def test_build_scoring_prompt_ignores_ranking_threshold_config() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
        config={"fit_label_thresholds": {"strong": 0.8, "stretch": 0.55}},
    )
    assert "0.8" not in prompt
    assert "0.55" not in prompt


def test_build_scoring_prompt_empty_evidence_does_not_crash() -> None:
    prompt = build_scoring_prompt(
        jd_summary="DE role",
        candidate_summary="candidate",
        top_evidence=[],
    )
    assert isinstance(prompt, str)
    assert len(prompt) > 0


# ── parse_score_response ──────────────────────────────────────────────────────

def test_parse_score_response_valid_json() -> None:
    result = parse_score_response(_VALID_RESPONSE)
    assert result["ai_score"] == 0.85
    assert result["legacy_model_fit_label"] == "strong"
    assert result["matched_strengths"] == ["SQL", "Python", "BigQuery"]
    assert isinstance(result["key_risks"], list)


def test_parse_score_response_returns_all_required_keys() -> None:
    result = parse_score_response(_VALID_RESPONSE)
    assert {
        "ai_score",
        "legacy_model_fit_label",
        "score_reasoning",
        "matched_strengths",
        "key_risks",
    } <= set(result.keys())


def test_parse_score_response_score_clamped_below_upper_bound() -> None:
    raw = json.dumps({
        "ai_score": 1.5, "fit_label": "strong",
        "score_reasoning": "", "matched_strengths": [], "key_risks": [],
    })
    result = parse_score_response(raw)
    assert result["ai_score"] <= 1.0


def test_parse_score_response_score_clamped_above_lower_bound() -> None:
    raw = json.dumps({
        "ai_score": -0.5, "fit_label": "skip",
        "score_reasoning": "", "matched_strengths": [], "key_risks": [],
    })
    result = parse_score_response(raw)
    assert result["ai_score"] >= 0.0


def test_parse_score_response_bad_fit_label_dropped() -> None:
    raw = json.dumps({
        "ai_score": 0.3, "fit_label": "maybe",
        "score_reasoning": "", "matched_strengths": [], "key_risks": [],
    })
    result = parse_score_response(raw)
    assert result["legacy_model_fit_label"] is None


def test_parse_score_response_malformed_json_returns_defaults() -> None:
    result = parse_score_response("not json at all")
    assert result["ai_score"] == 0.0
    assert result["legacy_model_fit_label"] is None
    assert result["score_reasoning"] == "Scoring response parse failure: malformed_json"
    assert result["parser_status"] == "malformed_json"
    assert result["matched_strengths"] == []
    assert result["key_risks"] == []


def test_parse_score_response_markdown_fenced_json() -> None:
    """Model sometimes wraps response in ```json ... ``` fences."""
    raw = '```json\n{"ai_score": 0.75, "fit_label": "strong", "score_reasoning": "good", "matched_strengths": [], "key_risks": []}\n```'
    result = parse_score_response(raw)
    assert result["ai_score"] == 0.75
    assert result["legacy_model_fit_label"] == "strong"


def test_parse_score_response_does_not_derive_fit_label() -> None:
    raw = json.dumps({
        "ai_score": 0.8,
        "score_reasoning": "good match",
        "matched_strengths": ["SQL"],
        "key_risks": [],
    })
    result = parse_score_response(raw)
    assert result["legacy_model_fit_label"] is None


def test_score_job_uses_shared_runtime_contract() -> None:
    from unittest.mock import patch

    from fitcv.ai_score import _execute_ranking_runtime, score_job
    from fitcv.llm_runtime import LlmAdapterResponse
    from fitcv.runtime_routing import LlmRouting

    route = LlmRouting(
        provider="openai_compatible",
        base_url="https://provider.example/v1",
        wire_api="responses",
        model="cx/test-model",
        timeout_seconds=12.0,
    )
    captured: dict[str, object] = {}

    def adapter(request, routing, api_key):
        captured["request"] = request
        return LlmAdapterResponse(
            raw_text=(
                '{"ai_score":0.8,"fit_label":"strong","score_reasoning":"good",'
                '"matched_strengths":[],"key_risks":[]}'
            ),
            adapter="fake",
            runtime_path="test",
        )

    job = {"job_url": "http://test.url/1", "title": "Data Engineer"}
    with (
        patch("fitcv.llm_runtime.resolve_llm_routing", return_value=route),
        patch("fitcv.llm_runtime.resolve_llm_api_key", return_value="secret"),
    ):
        runtime_result = _execute_ranking_runtime(
            job,
            "candidate summary",
            [],
            {},
            adapter=adapter,
        )

    with patch("fitcv.ai_score._execute_ranking_runtime", return_value=runtime_result):
        result = score_job(job, "candidate summary", [], {})

    request = captured["request"]
    assert request.routing_part == "ranking_ai_score"
    assert request.response_mode == "json_object"
    assert result["job_url"] == "http://test.url/1"
    assert result["ai_score"] == 0.8

def test_run_ai_scoring_prefers_nested_pipeline_top_n_over_legacy_flat_key() -> None:
    from fitcv.ai_score import run_ai_scoring

    shortlist = [
        {"job_url": "https://example.com/1"},
        {"job_url": "https://example.com/2"},
        {"job_url": "https://example.com/3"},
    ]

    with patch("fitcv.ai_score.score_job") as mock_score_job, patch.object(time, "sleep"):
        mock_score_job.side_effect = lambda **kwargs: {
            "job_url": kwargs["job"]["job_url"],
            "ai_score": 0.5,
            "fit_label": "stretch",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }
        results = run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 1},
                "rerank_top_n": 3,
                "rerank_sleep_secs": 0.0,
            },
        )

    assert len(results) == 1
    assert mock_score_job.call_count == 1
    assert results[0]["job_url"] == "https://example.com/1"

def test_run_ai_scoring_prefers_stage_runtime_ranking_sleep_over_legacy() -> None:
    from fitcv.ai_score import run_ai_scoring

    shortlist = [
        {"job_url": "https://example.com/1"},
        {"job_url": "https://example.com/2"},
    ]
    sleep_calls: list[float] = []

    with patch("fitcv.ai_score.score_job") as mock_score_job, patch.object(time, "sleep") as mock_sleep:
        mock_score_job.side_effect = lambda **kwargs: {
            "job_url": kwargs["job"]["job_url"],
            "ai_score": 0.5,
            "fit_label": "stretch",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }
        mock_sleep.side_effect = lambda secs: sleep_calls.append(float(secs))
        run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 2},
                "rerank_sleep_secs": 0.9,
                "stage_runtime": {"ranking": {"sleep_secs": 0.2}},
            },
        )

    assert sleep_calls == [0.2]


def test_run_ai_scoring_parallel_path_preserves_input_order() -> None:
    from fitcv.ai_score import run_ai_scoring

    shortlist = [
        {"job_url": "https://example.com/1"},
        {"job_url": "https://example.com/2"},
        {"job_url": "https://example.com/3"},
    ]

    def _slow_score_job(*, job: dict[str, Any], **_: Any) -> dict[str, Any]:
        if job["job_url"].endswith("/1"):
            time.sleep(0.03)
        elif job["job_url"].endswith("/2"):
            time.sleep(0.01)
        return {
            "job_url": job["job_url"],
            "ai_score": 0.5,
            "fit_label": "stretch",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }

    with patch("fitcv.ai_score.score_job", side_effect=_slow_score_job):
        results = run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 3},
                "stage_runtime": {"ranking": {"concurrency": 3, "sleep_secs": 0.0}},
            },
        )

    assert [row["job_url"] for row in results] == [job["job_url"] for job in shortlist]


def test_run_ai_scoring_parallel_path_isolates_runtime_exceptions() -> None:
    from fitcv.ai_score import run_ai_scoring

    shortlist = [
        {"job_url": "https://example.com/1"},
        {"job_url": "https://example.com/2"},
    ]

    def _score_or_fail(*, job: dict[str, Any], **_: Any) -> dict[str, Any]:
        if job["job_url"].endswith("/2"):
            raise RuntimeError("boom")
        return {
            "job_url": job["job_url"],
            "ai_score": 0.8,
            "legacy_model_fit_label": "strong",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }

    with patch("fitcv.ai_score.score_job", side_effect=_score_or_fail):
        results = run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 2},
                "stage_runtime": {"ranking": {"concurrency": 2, "sleep_secs": 0.0}},
            },
        )

    assert results[0]["job_url"] == "https://example.com/1"
    assert results[0]["legacy_model_fit_label"] == "strong"
    assert results[1]["job_url"] == "https://example.com/2"
    assert results[1]["legacy_model_fit_label"] is None
    assert results[1]["parser_status"] == "runtime_exception"

def test_run_ai_scoring_parallel_path_overlaps_workers_when_sleep_zero() -> None:
    from fitcv.ai_score import run_ai_scoring

    shortlist = [
        {"job_url": "https://example.com/1"},
        {"job_url": "https://example.com/2"},
    ]
    barrier = threading.Barrier(2)

    def _score_with_barrier(*, job: dict[str, Any], **_: Any) -> dict[str, Any]:
        barrier.wait(timeout=0.5)
        return {
            "job_url": job["job_url"],
            "ai_score": 0.6,
            "fit_label": "stretch",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }

    with patch("fitcv.ai_score.score_job", side_effect=_score_with_barrier):
        results = run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 2},
                "stage_runtime": {"ranking": {"concurrency": 2, "sleep_secs": 0.0}},
            },
        )

    assert len(results) == 2

def test_run_ai_scoring_parallel_path_still_paces_submission_when_sleep_positive() -> None:
    from fitcv.ai_score import run_ai_scoring

    shortlist = [
        {"job_url": "https://example.com/1"},
        {"job_url": "https://example.com/2"},
        {"job_url": "https://example.com/3"},
    ]
    sleep_calls: list[float] = []

    with patch("fitcv.ai_score.score_job") as mock_score_job, patch.object(time, "sleep") as mock_sleep:
        mock_score_job.side_effect = lambda **kwargs: {
            "job_url": kwargs["job"]["job_url"],
            "ai_score": 0.5,
            "fit_label": "stretch",
            "score_reasoning": "ok",
            "matched_strengths": [],
            "key_risks": [],
        }
        mock_sleep.side_effect = lambda secs: sleep_calls.append(float(secs))
        run_ai_scoring(
            shortlist=shortlist,
            candidate_summary="candidate",
            config={
                "pipeline": {"ai_score_top_n": 3},
                "stage_runtime": {"ranking": {"concurrency": 3, "sleep_secs": 0.2}},
            },
        )

    assert sleep_calls == [0.2, 0.2]


# ── store_ai_scores ───────────────────────────────────────────────────────────


def test_store_ai_scores_writes_sqlite_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fitcv.ai_score import store_ai_scores

    db_path = tmp_path / "fitcv_cp.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))

    scores = [
        {
            "job_url": "https://example.com/job-1",
            "ai_score": 0.91,
            "legacy_model_fit_label": "strong",
            "score_reasoning": "Strong SQL and Python fit",
            "matched_strengths": ["SQL", "Python"],
            "key_risks": ["No dbt"],
        },
        {
            "job_url": "https://example.com/job-2",
            "ai_score": 0.55,
            "legacy_model_fit_label": "stretch",
            "score_reasoning": "Partial analytics overlap",
            "matched_strengths": ["Looker"],
            "key_risks": [],
        },
    ]

    store_ai_scores(scores, config={})

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT job_url, ai_score, fit_label, score_reasoning,
                   matched_strengths_json, key_risks_json
            FROM ai_score_results
            ORDER BY job_url
            """
        ).fetchall()

    assert len(rows) == 2
    assert rows[0][0] == "https://example.com/job-1"
    assert float(rows[0][1]) == 0.91
    assert rows[0][2] == "strong"
    assert json.loads(str(rows[0][4])) == ["SQL", "Python"]
    assert json.loads(str(rows[0][5])) == ["No dbt"]
    assert rows[1][0] == "https://example.com/job-2"
    assert float(rows[1][1]) == 0.55
    assert rows[1][2] == "stretch"
    assert json.loads(str(rows[1][4])) == ["Looker"]
    assert json.loads(str(rows[1][5])) == []



# ── integration tests ─────────────────────────────────────────────────────────

@pytest.mark.integration
def test_score_job_integration(config: dict) -> None:
    """Integration — calls routed OpenAI-compatible scoring provider and returns a parsed score."""
    from fitcv.ai_score import score_job
    job = {
        "job_url": "http://test.url/1",
        "title": "Data Engineer",
        "required_skills": ["SQL", "Python"],
        "seniority": "mid",
        "job_family": "data_engineering",
        "responsibilities": ["Build pipelines", "Write tests"],
    }
    result = score_job(
        job=job,
        candidate_summary="Experienced data engineer with 4 years SQL and Python.",
        top_evidence=["Built GA4 pipeline reducing latency 40%."],
        config=config,
    )
    assert 0.0 <= result["ai_score"] <= 1.0
    assert "fit_label" not in result
"""
@meta
type: test
scope: unit
domain: ranking
covers:
  - AI scoring behavior
excludes:
  - live model calls
tags:
  - fast
  - ci-safe
"""


def test_execute_ranking_runtime_keeps_empty_output_stage_owned() -> None:
    from unittest.mock import patch

    from fitcv.ai_score import _execute_ranking_runtime
    from fitcv.llm_runtime import LlmAdapterResponse
    from fitcv.runtime_routing import LlmRouting

    route = LlmRouting(
        provider="openai_compatible",
        base_url="https://provider.example/v1",
        wire_api="responses",
        model="cx/test-model",
        timeout_seconds=12.0,
    )
    captured: dict[str, object] = {}

    def adapter(request, routing, api_key):
        captured["request"] = request
        return LlmAdapterResponse(raw_text="", adapter="fake", runtime_path="test")

    with (
        patch("fitcv.llm_runtime.resolve_llm_routing", return_value=route),
        patch("fitcv.llm_runtime.resolve_llm_api_key", return_value="secret"),
    ):
        result = _execute_ranking_runtime(
            {"job_url": "https://example.com/1", "title": "Data Engineer"},
            "candidate",
            [],
            {},
            adapter=adapter,
        )

    request = captured["request"]
    assert request.routing_part == "ranking_ai_score"
    assert request.response_mode == "json_object"
    assert result.status == "succeeded"
    assert result.parsed_value["parser_status"] == "malformed_json"


def test_run_ai_scoring_emits_stable_runtime_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    from fitcv.ai_score import run_ai_scoring
    from fitcv.llm_runtime import LlmRuntimeProvenance, LlmRuntimeResult, LlmValidationResult

    runtime_result = LlmRuntimeResult(
        status="succeeded",
        parsed_value={
            "ai_score": 0.9,
            "legacy_model_fit_label": "strong",
            "score_reasoning": "match",
            "matched_strengths": [],
            "key_risks": [],
            "parser_status": "ok",
        },
        validation=LlmValidationResult(valid=True, errors=[], details={}),
        failure=None,
        provenance=LlmRuntimeProvenance(
            routing_part="ranking_ai_score",
            runtime_path="test",
            adapter="fake",
            provider="test",
            model="test",
            wire_api="responses",
            attempt_count=1,
            response_id=None,
            trace_id=None,
            latency_ms=1,
        ),
        adapter_response=None,
    )
    monkeypatch.setattr("fitcv.ai_score._execute_ranking_runtime", lambda *args, **kwargs: runtime_result)
    observations: list[dict[str, Any]] = []

    rows = run_ai_scoring(
        [{"job_url": "https://example.com/jobs/1", "raw_job_fingerprint": "raw-1"}],
        "candidate",
        {"stage_runtime": {"ranking": {"sleep_secs": 0}}},
        runtime_observation_callback=observations.append,
    )

    assert rows[0]["job_url"] == "https://example.com/jobs/1"
    assert observations == [
        {
            "contract_version": "llm_runtime_observation_v1",
            "scope_key": "raw-1",
            "input_index": 0,
            "invocation_index": 1,
            "evidence": {
                "contract_version": "llm_runtime_evidence_v1",
                "status": "succeeded",
                "provenance": {
                    "routing_part": "ranking_ai_score",
                    "runtime_path": "test",
                    "adapter": "fake",
                    "provider": "test",
                    "model": "test",
                    "wire_api": "responses",
                    "attempt_count": 1,
                    "response_id": None,
                    "trace_id": None,
                    "latency_ms": 1,
                },
                "failure": None,
            },
        }
    ]
