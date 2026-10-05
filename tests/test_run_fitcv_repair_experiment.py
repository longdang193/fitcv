from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import run_fitcv_repair_experiment as experiment
from scripts.run_fitcv_repair_experiment import (
    _disable_cross_run_reuse,
    _enable_frozen_upstream_reuse,
    _experiment_jobs,
    _require_fresh_path,
    _response_run_id,
    _stabilize_experiment_llm_configuration,
    _validate_job_types_against_exclusions,
)


def test_experiment_jobs_keep_each_declared_job_type() -> None:
    jobs = _experiment_jobs(["Internship", "Part-time"])

    assert [job["contractType"] for job in jobs] == ["Internship", "Part-time"]
    assert len({job["jobUrl"] for job in jobs}) == 2


def test_experiment_job_identity_does_not_collide_across_repeated_submissions() -> None:
    jobs = [*_experiment_jobs(["Contract"]), *_experiment_jobs(["Part-time"])]

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


def test_experiment_settings_freeze_upstream_analysis_but_not_generation() -> None:
    settings = {
        "reuse": {"cv_generation": {"enabled": True}},
        "pipeline": {"final_top_n": 3},
    }

    frozen = _enable_frozen_upstream_reuse(settings)

    assert frozen["pipeline"] == settings["pipeline"]
    assert all(
        frozen["reuse"][stage]["enabled"] is (stage != "cv_generation")
        for stage in ("enrich", "ranking", "cv_analysis", "cv_generation", "synonym_triage")
    )
    assert frozen["experiment_reuse_policy"] == "frozen_upstream_analysis_v1"
    assert settings["reuse"]["cv_generation"]["enabled"] is True


def test_llm_configuration_stabilization_is_idempotent_for_seeded_cohort(tmp_path: Path) -> None:
    database = tmp_path / "cohort.sqlite3"
    resource = {
        "tasks": {
            "enrich_extraction": {"temperature": 0.4},
            "ranking_ai_score": {"temperature": 0.2},
        }
    }
    import sqlite3

    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE configuration_resources (resource_name TEXT PRIMARY KEY, resource_json TEXT, revision INTEGER, updated_at TEXT)"
        )
        connection.execute(
            "INSERT INTO configuration_resources VALUES (?, ?, ?, ?)",
            ("llm_configuration", json.dumps(resource), 7, "before"),
        )
        connection.commit()

    _stabilize_experiment_llm_configuration(database)
    with sqlite3.connect(database) as connection:
        first = connection.execute(
            "SELECT resource_json, revision FROM configuration_resources WHERE resource_name = ?",
            ("llm_configuration",),
        ).fetchone()

    _stabilize_experiment_llm_configuration(database)
    with sqlite3.connect(database) as connection:
        second = connection.execute(
            "SELECT resource_json, revision FROM configuration_resources WHERE resource_name = ?",
            ("llm_configuration",),
        ).fetchone()

    assert first is not None and second is not None
    assert json.loads(first[0]) == json.loads(second[0])
    assert first[1] == second[1] == 8


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
    fixture = tmp_path / "tests" / "fixtures" / "fitcv-p1ab-repair-experiment.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text(json.dumps(_fixture_payload()), encoding="utf-8")
    profile_directory = tmp_path / "data"
    profile_directory.mkdir()
    profile_directory.joinpath("candidate_profile.yaml").write_text(
        "preferences:\n  exclude_contract_types: []\n",
        encoding="utf-8",
    )
    profile_directory.joinpath("candidate_profile.private.yaml").write_text(
        "private: true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(experiment, "ROOT", tmp_path)
    monkeypatch.setattr(
        experiment,
        "DECLARED_INPUTS",
        ("data/candidate_profile.yaml", "data/candidate_profile.private.yaml"),
    )
    monkeypatch.setattr(experiment, "_git", lambda *args: "unchanged")
    monkeypatch.setattr(experiment, "_diff_hash", lambda: "unchanged")
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


def test_declared_inputs_cover_private_profile_and_analysis_generation_runtime_store() -> None:
    assert {
        "data/candidate_profile.private.yaml",
        "src/fitcv/agentic_cv_analysis.py",
        "src/fitcv/contracts.py",
        "src/fitcv/cv_generator.py",
        "src/fitcv/evidence.py",
        "src/fitcv/llm_runtime.py",
        "src/fitcv/openai_compat.py",
        "src/fitcv/runtime_routing.py",
        "src/fitcv/prompts/__init__.py",
        "src/fitcv/prompts/loader.py",
        "src/fitcv/prompts/models.py",
        "src/fitcv/prompts/registry.py",
        "src/fitcv/prompts/renderer.py",
        "src/fitcv/prompts/templates/cv_generation_write_v1.md",
        "src/fitcv_cp/run_artifact_contracts.py",
        "src/fitcv_cp/local_storage.py",
        "config/runtime/prompts.yaml",
        "templates/cv_template.md",
        "src/fitcv_cp/sqlite_store.py",
    }.issubset(experiment.DECLARED_INPUTS)


@pytest.mark.parametrize(
    "relative_path",
    [
        "src/fitcv/llm_runtime.py",
        "src/fitcv/runtime_routing.py",
        "src/fitcv/validator.py",
        "src/fitcv/evidence.py",
        "src/fitcv/openai_compat.py",
        "src/fitcv/contracts.py",
        "src/fitcv/cv_presets.py",
        "src/fitcv/prompts/__init__.py",
        "src/fitcv_cp/local_storage.py",
        "templates/cv_template.md",
        "config/runtime/prompts.yaml",
        "src/fitcv_cp/run_artifact_contracts.py",
    ],
)
def test_declared_input_fingerprint_changes_when_material_dependency_changes(
    monkeypatch, tmp_path: Path, relative_path: str
) -> None:
    fixture = tmp_path / "tests" / "fixtures" / "fitcv-p1ab-repair-experiment.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("{}", encoding="utf-8")
    for declared in experiment.DECLARED_INPUTS:
        path = tmp_path / declared
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("baseline", encoding="utf-8")
    monkeypatch.setattr(experiment, "ROOT", tmp_path)

    baseline = experiment._input_fingerprint(fixture)
    (tmp_path / relative_path).write_text("changed", encoding="utf-8")

    assert experiment._input_fingerprint(fixture) != baseline
