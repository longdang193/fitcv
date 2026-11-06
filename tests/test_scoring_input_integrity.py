import json
from types import SimpleNamespace

from fitcv.ai_score import build_ranking_request
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
