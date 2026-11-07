import json
from types import SimpleNamespace

from fitcv.ai_score import build_ranking_job_input, build_ranking_request, run_ai_scoring
from fitcv.rule_filter import apply_rule_filters


def _route() -> SimpleNamespace:
    return SimpleNamespace(
        provider="openai_compatible",
        base_url="https://provider.example/v1",
        wire_api="responses",
        model="test-model",
        timeout_seconds=12.0,
        request_start_interval_secs=0.0,
        auth_mode="env",
        temperature=0.0,
        model_record_id="model-record",
        configuration_revision="config-revision",
    )


def test_final_scorer_request_retains_language_dimensions_and_ongoing_education() -> None:
    job = {
        "job_url": "https://example.com/job",
        "title": "Data Analyst",
        "required_skills": ["SQL"],
        "language_requirements": [{"name": "German", "level": "B1"}],
        "education": [{"degree": "Master", "field": "Data Science", "status": "ongoing"}],
    }
    candidate_summary = json.dumps({
        "skills": ["SQL"],
        "languages": [{
            "name": "German",
            "level": "B1",
            "native": False,
            "read": "B1",
            "write": "A2",
            "speak": "B1",
        }],
        "employment": [],
        "education": [{
            "institution": "Example University",
            "degree": "Master",
            "field": "Data Science",
            "start": "2024-10",
            "end": "Present",
        }],
        "certifications": [],
        "years_experience": 2,
        "target_role": "Data Analyst",
    }, ensure_ascii=False)
    ranking_input = {
        "candidate_summary": candidate_summary,
        "job_requirements": "SQL, German B1, ongoing Master Data Science",
        "candidate_evidence": [{
            "evidence_id": "ev-education-language",
            "text": "German B1; ongoing Master Data Science",
            "source_refs": [{"document_id": "cv-1", "source_block_id": "education-1"}],
        }],
    }
    request = build_ranking_request(
        job,
        candidate_summary,
        [],
        {},
        ranking_input=ranking_input,
        resolved_route=_route(),
    )

    prompt = request["request"].prompt
    assert '"read": "B1"' in prompt
    assert '"write": "A2"' in prompt
    assert '"speak": "B1"' in prompt
    assert "ongoing" in prompt
    assert len(json.dumps(request["request_payload"], ensure_ascii=False)) <= 12_000


def test_ranking_input_preserves_dimension_only_and_native_language_records() -> None:
    ranking_input = build_ranking_job_input(
        {"job_url": "https://example.com/job", "required_skills": []},
        {
            "languages": [
                {"id": "language-german", "name": "German", "read": "B2", "write": "B1", "speak": "B1"},
                {"id": "language-french", "name": "French", "native": True},
            ]
        },
        {},
    )

    languages = json.loads(ranking_input["candidate_summary"])["languages"]
    assert languages == [
        {"level": "b1", "name": "German", "read": "B2", "write": "B1", "speak": "B1"},
        {"level": "native", "name": "French", "native": True},
    ]


def test_ranking_input_preserves_source_text_separately_from_scoring_context() -> None:
    ranking_input = build_ranking_job_input(
        {"job_url": "https://example.com/job", "required_skills": ["Python"]},
        {
            "_projected_evidence_pool": [{
                "evidence_id": "ev-1",
                "kind": "project",
                "text": "Built a Python service.",
                "scoring_context": "Python service; reduced latency by 40%.",
                "source_refs": [{"document_id": "doc-1", "source_block_id": "block-1"}],
            }],
        },
        {},
    )

    evidence = ranking_input["candidate_evidence"][0]
    assert evidence["text"] == "Built a Python service."
    assert evidence["scoring_context"] == "Python service; reduced latency by 40%."
    assert evidence["source_refs"] == [{"document_id": "doc-1", "source_block_id": "block-1"}]


def test_missing_candidate_skill_is_not_reported_as_budget_omission() -> None:
    job = {
        "job_url": "https://example.com/job",
        "title": "Scala Engineer",
        "required_skills": ["Scala"],
    }
    profile = {
        "skills": ["Python"],
        "_projected_evidence_pool": [{
            "evidence_id": "ev-python",
            "text": "Built Python services.",
            "source_refs": [{"document_id": "cv-1"}],
        }],
    }
    ranking_input = build_ranking_job_input(job, profile, {})

    request = build_ranking_request(
        job,
        ranking_input["candidate_summary"],
        ranking_input["candidate_evidence"],
        {},
        ranking_input=ranking_input,
        resolved_route=_route(),
    )

    assert request["visibility_manifest"]["mandatory_core_complete"] is True


def test_run_ai_scoring_marks_explicit_empty_evidence_unavailable_without_provider_call(monkeypatch) -> None:
    def fail_provider(*_args, **_kwargs):
        raise AssertionError("provider scoring must not run without selected evidence")

    monkeypatch.setattr("fitcv.ai_score.score_job", fail_provider)
    result = run_ai_scoring(
        [{
            "job_url": "https://example.com/no-evidence",
            "ranking_input": {
                "candidate_summary": "candidate",
                "job_requirements": "SQL",
                "candidate_evidence": [],
            },
        }],
        "candidate",
        {},
    )[0]

    assert result["score_status"] == "unscored"
    assert result["failure_code"] == "evidence_limited"
    assert result["disposition"] == "unavailable"
    assert result["retry_eligible"] is False


def test_run_ai_scoring_keeps_budget_only_evidence_failure_retryable(monkeypatch) -> None:
    monkeypatch.setattr("fitcv.ai_score.RANKING_REQUEST_MAX_CHARS", 100)
    monkeypatch.setattr("fitcv.ai_score.build_scoring_prompt", lambda *_args, **_kwargs: "x" * 500)
    monkeypatch.setattr("fitcv.ai_score.score_job", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("provider scoring must not run after budget failure")))

    result = run_ai_scoring(
        [{
            "job_url": "https://example.com/budget",
            "ranking_input": {
                "candidate_summary": "candidate",
                "job_requirements": "SQL",
                "candidate_evidence": [{
                    "evidence_id": "ev-1",
                    "text": "Built SQL pipelines.",
                    "source_ref": "cv:project:sql",
                }],
            },
        }],
        "candidate",
        {},
    )[0]

    assert result["score_status"] == "unscored"
    assert result["failure_code"] == "budget_exceeded"
    assert result["disposition"] == "retryable_failure"
    assert result["retry_eligible"] is True


def test_raw_description_or_substantive_requirement_survives_missing_fit_context() -> None:
    result = apply_rule_filters(
        [{
            "job_url": "https://example.com/job",
            "title": "Platform Engineer",
            "description": "Build SQL and BigQuery data pipelines.",
            "required_skills": [],
            "seniority": None,
            "location_type": None,
            "job_family": None,
            "domain": None,
        }],
        {"seniority_target": "mid", "location_types": [], "contract_types": []},
    )

    assert result["passed"] == ["https://example.com/job"]
    assert result["rejected"] == []
    assert result["passed_records"][0]["marks"][0]["code"] == "missing_fit_context"
