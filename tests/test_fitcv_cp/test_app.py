from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fitcv_cp.app import create_app


def _app():
    bq = MagicMock()
    return create_app(bq=bq, project="p", dataset="d", redis_url="redis://localhost:6379/0")


def test_post_runs_inserts_before_enqueue():
    """BQ insert must happen before enqueue to ensure DB is source of truth."""
    call_order = []

    def fake_insert(*args, **kwargs):
        call_order.append("insert")

    def fake_enqueue(*args, **kwargs):
        call_order.append("enqueue")
        return "run-123"

    with patch("fitcv_cp.app.insert_run", side_effect=fake_insert), \
         patch("fitcv_cp.app.enqueue_run", side_effect=fake_enqueue):
        resp = TestClient(_app()).post("/runs", json={"jobs_path": "data/sample_jobs.json"})
    assert resp.status_code == 201
    assert "run_id" in resp.json()
    assert call_order == ["insert", "enqueue"], f"Order was: {call_order}"


def test_post_runs_rejects_empty_jobs_path():
    resp = TestClient(_app()).post("/runs", json={"jobs_path": ""})
    assert resp.status_code == 422


def test_get_runs_returns_list():
    with patch("fitcv_cp.app.list_runs", return_value=[]):
        resp = TestClient(_app()).get("/runs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_run_detail_not_found():
    with patch("fitcv_cp.app.get_run", return_value=None):
        resp = TestClient(_app()).get("/runs/missing-id")
    assert resp.status_code == 404


def test_get_run_events():
    with patch("fitcv_cp.app.get_run", return_value=MagicMock()), \
         patch("fitcv_cp.app.get_events", return_value=[]):
        resp = TestClient(_app()).get("/runs/some-id/events")
    assert resp.status_code == 200


def test_healthz():
    resp = TestClient(_app()).get("/healthz")
    assert resp.status_code == 200
