from __future__ import annotations

from pathlib import Path

import pytest

from fitcv_cp import sqlite_store
from fitcv.runtime_routing import LlmRouting, resolve_llm_api_key
from scripts.run_fitcv_local_p0_acceptance import _job_url
from tests.test_fitcv_cp.acceptance_harness import (
    ControlledLocalJobExecutor,
    configure_local_provider_credential_from_env,
    create_profile_fixture,
    create_scan_fixture,
)


@pytest.mark.parametrize("job", [
    {"jobUrl": "https://example.test/camel"},
    {"job_url": "https://example.test/snake"},
    {"url": "https://example.test/fallback"},
])
def test_acceptance_job_url_reader_accepts_runtime_key_shapes(job: dict[str, str]) -> None:
    assert _job_url(job) == next(iter(job.values()))


def test_controlled_executor_holds_until_release_and_captures_result() -> None:
    with ControlledLocalJobExecutor() as executor:
        future = executor.submit(lambda value: value, "snapshot-A")
        executor.wait_submitted()
        assert not future.done()
        executor.release()
        assert executor.result() == "snapshot-A"


def test_controlled_executor_releases_exactly_once() -> None:
    with ControlledLocalJobExecutor() as executor:
        executor.submit(lambda: None)
        executor.wait_submitted()
        executor.release()
        with pytest.raises(RuntimeError, match="already released"):
            executor.release()


def test_controlled_executor_preserves_worker_exception() -> None:
    def fail() -> None:
        raise ValueError("fixture failure")

    with ControlledLocalJobExecutor() as executor:
        executor.submit(fail)
        executor.wait_submitted()
        executor.release()
        with pytest.raises(ValueError, match="fixture failure"):
            executor.result()

def test_controlled_executor_can_inject_one_local_failure() -> None:
    with ControlledLocalJobExecutor() as executor:
        executor.submit(lambda: None)
        executor.wait_submitted()
        executor.fail_next(RuntimeError("acceptance injected failure"))
        executor.release()
        with pytest.raises(RuntimeError, match="acceptance injected failure"):
            executor.result()


def test_configure_local_provider_credential_from_env_persists_loaded_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setenv("FITCV_LLM_API_KEY", "dotenv-secret")
    monkeypatch.setattr(
        "fitcv_cp.local_credentials.set_credential",
        lambda provider_id, api_key: calls.append((provider_id, api_key)),
    )

    assert configure_local_provider_credential_from_env("openai_compatible") is True
    assert calls == [("openai_compatible", "dotenv-secret")]


def test_configure_local_provider_credential_from_env_rejects_missing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FITCV_LLM_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="FITCV_LLM_API_KEY is required"):
        configure_local_provider_credential_from_env("openai_compatible")


def test_configure_local_provider_credential_from_env_matches_custom_runtime_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials: dict[str, str] = {}
    monkeypatch.setenv("FITCV_LOCAL_MODE", "1")
    monkeypatch.setenv("FITCV_LLM_API_KEY", "dotenv-secret")
    monkeypatch.setattr(
        "fitcv_cp.local_credentials.set_credential",
        lambda provider_id, api_key: credentials.__setitem__(provider_id, api_key),
    )
    monkeypatch.setattr(
        "fitcv_cp.local_credentials.get_credential",
        lambda provider_id: credentials.get(provider_id, ""),
    )

    provider_id = "custom-acceptance-gateway"
    assert configure_local_provider_credential_from_env(provider_id) is True

    route = LlmRouting(
        provider=provider_id,
        base_url="http://127.0.0.1:20128/v1",
        wire_api="responses",
        model="test-model",
        timeout_seconds=30,
    )
    assert resolve_llm_api_key(route) == "dotenv-secret"


def test_scan_fixture_is_disposable_and_run_eligible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database_path = tmp_path / "acceptance.sqlite3"
    profile_path = Path(__file__).parents[2] / "data" / "candidate_profile.private.yaml"
    sqlite_store.initialize_control_plane_database(database_path, profile_path)
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(database_path))

    jobs = [{
        "jobUrl": "https://acceptance.example/job-1",
        "title": "Data Analyst",
        "companyName": "Acceptance Company",
        "description": "Analyze product data with SQL and Python.",
        "contractType": "Full-time",
        "experienceLevel": "Mid-Senior level",
        "location": "Berlin, Germany",
    }]
    scan = create_scan_fixture(database_path, scan_name="Acceptance Scan A", jobs=jobs)

    assert scan["execution_status"] == "succeeded"
    assert scan["output_record_count"] == 1
    assert scan["output_integrity_valid"] is True
    assert scan["capabilities"]["use_for_run"] is True
    assert sqlite_store.get_scan_output(scan["scan_id"], database_path=database_path)["output_json"]


def test_profile_fixture_is_active_and_v2(tmp_path: Path) -> None:
    database_path = tmp_path / "acceptance.sqlite3"
    profile_path = Path(__file__).parents[2] / "data" / "candidate_profile.private.yaml"
    sqlite_store.initialize_control_plane_database(database_path, profile_path)
    from tests.test_fitcv_cp.candidate_profile_fixtures import CandidateProfileMockState, _baseline_document, _derived_document

    canonical = CandidateProfileMockState._canonical(_baseline_document(), _derived_document())
    profile = create_profile_fixture(database_path, canonical)

    assert profile["creation_status"] == "succeeded"
    assert profile["lifecycle"] == "active"
    assert profile["is_active"] is True
    assert profile["profile"]["schema_version"] == "candidate-profile.v2"
