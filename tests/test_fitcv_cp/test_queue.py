from unittest.mock import MagicMock, patch
from fitcv_cp.queue import enqueue_run


def test_enqueue_run_returns_uuid():
    mock_q = MagicMock()
    with patch("fitcv_cp.queue.get_queue", return_value=mock_q):
        run_id = enqueue_run(
            jobs_path="data/sample_jobs.json",
            config_path=".env.yaml",
            triggered_by="admin",
            redis_url="redis://localhost:6379/0",
        )
    assert isinstance(run_id, str) and len(run_id) == 36
    mock_q.enqueue.assert_called_once()
