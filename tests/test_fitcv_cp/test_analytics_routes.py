from pathlib import Path

from fastapi.testclient import TestClient

from scripts.refresh_fitcv_analytics import refresh_analytics
from tests.test_export_fitcv_analytics_source import _seed_database
from fitcv_cp.app import create_app
from fitcv_cp.backend_runtime import set_backend_runtime


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)
    refresh_analytics(database, output_root, source_commit="dashboard-fixture")
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(database))
    monkeypatch.setenv("FITCV_ANALYTICS_OUTPUT_ROOT", str(output_root))
    monkeypatch.setenv("FITCV_ANALYTICS_SOURCE_COMMIT", "dashboard-fixture")
    monkeypatch.setenv("FITCV_CP_INLINE_EXECUTION", "1")
    set_backend_runtime(None)
    return TestClient(create_app(redis_url="redis://localhost:6379/0"))


def test_semantic_metrics_route_exposes_published_projections(tmp_path: Path, monkeypatch) -> None:
    with _client(tmp_path, monkeypatch) as client:
        response = client.get("/analytics/semantic-metrics")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["coverage"]["status"] == "available"
    assert payload["coverage"]["sample_size"] == 2
    assert payload["metadata"]["source_commit"] == "dashboard-fixture"
    assert payload["requirement_demand"]
    assert payload["candidate_evidence_gaps"]


def test_trace_route_returns_source_posting_chain(tmp_path: Path, monkeypatch) -> None:
    with _client(tmp_path, monkeypatch) as client:
        response = client.get("/analytics/trace/posting-hash")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["posting"]["posting_id"] == "posting-hash"
    assert payload["requirements"][0]["requirement"] == "python"


def test_missing_release_is_explicitly_unavailable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FITCV_ANALYTICS_OUTPUT_ROOT", str(tmp_path / "missing"))
    monkeypatch.setenv("FITCV_ANALYTICS_SOURCE_COMMIT", "dashboard-fixture")
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "operational.sqlite3"))
    monkeypatch.setenv("FITCV_CP_INLINE_EXECUTION", "1")
    set_backend_runtime(None)

    with TestClient(create_app(redis_url="redis://localhost:6379/0")) as client:
        response = client.get("/analytics/semantic-metrics")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["coverage"]["status"] == "unavailable"
    assert "unreadable:CURRENT.json" in payload["coverage"]["unavailable_reasons"]


def test_empty_projection_is_returned_without_claims(tmp_path: Path, monkeypatch) -> None:
    with _client(tmp_path, monkeypatch) as client:
        import fitcv_cp.app as app_module

        monkeypatch.setattr(
            app_module,
            "dashboard_payload",
            lambda _published: {
                "coverage": {
                    "status": "available",
                    "sample_size": 0,
                    "source_mix": [],
                    "collection_window": {"start": None, "end": None},
                    "candidate_revisions": [],
                    "unavailable_reasons": [],
                },
                "metadata": {},
                "opportunity_landscape": [],
                "requirement_demand": [],
                "candidate_evidence_gaps": [],
            },
        )
        response = client.get("/analytics/semantic-metrics")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["coverage"]["status"] == "available"
    assert payload["opportunity_landscape"] == []


def test_stale_release_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    with _client(tmp_path, monkeypatch) as client:
        monkeypatch.setenv("FITCV_ANALYTICS_SOURCE_COMMIT", "different-commit")
        response = client.get("/analytics/semantic-metrics")

    assert response.status_code == 200
    assert response.json()["data"]["coverage"]["unavailable_reasons"] == [
        "published_source_commit_stale"
    ]
