from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import run_fitcv_repair_experiment as experiment
from scripts.run_fitcv_repair_experiment import (
    _disable_cross_run_reuse,
    _experiment_jobs,
    _require_fresh_path,
    _response_run_id,
    _validate_job_types_against_exclusions,
)


def test_experiment_jobs_keep_each_declared_job_type() -> None:
    jobs = _experiment_jobs(["Internship", "Part-time"])

    assert [job["contractType"] for job in jobs] == ["Internship", "Part-time"]
    assert len({job["jobUrl"] for job in jobs}) == 2


def test_real_producer_rejects_existing_database(tmp_path: Path) -> None:
    path = tmp_path / "cohort.sqlite3"
    path.write_text("existing", encoding="utf-8")

    with pytest.raises(ValueError, match="path_must_be_fresh"):
        _require_fresh_path(path)


def test_experiment_settings_disable_cross_run_reuse_without_dropping_other_settings() -> None:
    settings = {
        "reuse": {"cv_generation": {"enabled": True}},
        "pipeline": {"final_top_n": 3},
    }

    isolated = _disable_cross_run_reuse(settings)

    assert isolated["pipeline"] == settings["pipeline"]
    assert all(
        isolated["reuse"][stage]["enabled"] is False
        for stage in ("enrich", "ranking", "cv_analysis", "cv_generation", "synonym_triage")
    )
    assert settings["reuse"]["cv_generation"]["enabled"] is True


def test_fixture_rejects_job_types_excluded_by_candidate_profile() -> None:
    with pytest.raises(ValueError, match="fixture_job_type_excluded_by_profile"):
        _validate_job_types_against_exclusions(["Part-time", "Internship"], ["Internship"])


@pytest.mark.parametrize("payload", [{"run_id": "top-level"}, {"data": {"run_id": "nested"}}])
def test_response_run_id_accepts_current_route_envelopes(payload: dict[str, object]) -> None:
    class Response:
        def json(self) -> dict[str, object]:
            return payload

    assert _response_run_id(Response()) in {"top-level", "nested"}


def _fixture_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "fitcv.p1ab.repair_experiment_fixture.v1",
        "model": "fixture-model",
        "runtime": "fitcv-runtime",
        "job_types": ["Part-time", "Contract"],
        "repeat_count": 10,
        "required_evidence_categories": ["grounding", "final_artifact", "page_fit", "review_outcome"],
        "arms": {"INCUMBENT_ARM": "local_first", "CANDIDATE_ARM": "provider_first"},
    }
    payload.update(overrides)
    return payload


def test_fixture_contract_type_exclusion_is_case_insensitive() -> None:
    with pytest.raises(ValueError, match="fixture_job_type_excluded_by_profile"):
        experiment._validate_job_types_against_exclusions(["contract", "Part-time"], ["Contract"])


def test_fixture_rejects_duplicate_normalized_job_types(tmp_path: Path) -> None:
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(_fixture_payload(job_types=["Contract", " contract "])), encoding="utf-8")

    with pytest.raises(ValueError, match="fixture_requires_unique_job_types"):
        experiment._load_fixture(path)


def test_fixture_rejects_unknown_required_evidence_category(tmp_path: Path) -> None:
    path = tmp_path / "fixture.json"
    path.write_text(
        json.dumps(_fixture_payload(required_evidence_categories=["grounding", "unknown"])),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="fixture_unknown_evidence_category:unknown"):
        experiment._load_fixture(path)


def test_manifest_rejects_changed_frozen_input_identity(monkeypatch, tmp_path: Path) -> None:
    fixture = experiment.DEFAULT_FIXTURE
    frozen = experiment.capture_input_identity(fixture)
    monkeypatch.setattr(experiment, "_git", lambda *args: "changed")

    with pytest.raises(ValueError, match="input_identity_changed_after_cohort"):
        experiment.build_manifest(
            fixture=fixture,
            arm="local_first",
            database=tmp_path / "cohort.sqlite3",
            run_ids=[f"run-{index}" for index in range(10)],
            frozen_input_identity=frozen,
        )
