"""
@meta
type: test
scope: unit
domain: run_orchestration
covers:
  - control-plane queue behavior
excludes:
  - live RQ workers
tags:
  - fast
  - ci-safe
"""

from unittest.mock import MagicMock, patch
from fitcv_cp.queue import enqueue_run
import fitcv_cp.queue as queue_module


def test_get_queue_is_cached_per_normalized_redis_url() -> None:
    queue_module._QUEUES_BY_REDIS_URL.clear()

    first_queue = MagicMock(name="queue-one")
    second_queue = MagicMock(name="queue-two")

    with patch("fitcv_cp.queue.redis.from_url", side_effect=[MagicMock(name="conn-one"), MagicMock(name="conn-two")]), \
         patch("fitcv_cp.queue.Queue", side_effect=[first_queue, second_queue]):
        assert queue_module.get_queue("redis://one:6379/0") is first_queue
        assert queue_module.get_queue("redis://one:6379/0") is first_queue
        assert queue_module.get_queue("redis://two:6379/0") is second_queue


def test_enqueue_run_returns_uuid():
    """@proves admin_control_plane_core.rq-background-worker-integration
    @proves trigger_run_management.manual-checkpoints-and-continue
    @proves trigger_run_management.runs-list-management
    """
    mock_q = MagicMock()
    with patch("fitcv_cp.queue.get_queue", return_value=mock_q):
        with patch.dict("os.environ", {"FITCV_CP_INLINE_EXECUTION": "0"}):
            run_id = enqueue_run(
                jobs_path="data/sample_jobs.json",
                config_path=".env.yaml",
                triggered_by="admin",
                redis_url="redis://localhost:6379/0",
            )
    assert isinstance(run_id, str) and len(run_id) == 36
    mock_q.enqueue.assert_called_once()


# ── enqueue_run_with_job_id ──────────────────────────────────────────────────

def test_enqueue_run_with_job_id_returns_tuple():
    """@proves admin_control_plane_core.rq-background-worker-integration"""
    from fitcv_cp.queue import enqueue_run_with_job_id
    mock_q = MagicMock()
    mock_job = MagicMock()
    mock_job.id = "rq-job-abc"
    mock_q.enqueue.return_value = mock_job
    with patch("fitcv_cp.queue.get_queue", return_value=mock_q):
        with patch.dict("os.environ", {"FITCV_CP_INLINE_EXECUTION": "0"}):
            run_id, job_id = enqueue_run_with_job_id(
                jobs_path="data/jobs.json",
                config_path=".env.yaml",
                triggered_by="admin",
                redis_url="redis://localhost:6379/0",
            )
    assert isinstance(run_id, str) and len(run_id) == 36
    assert job_id == "rq-job-abc"

def test_enqueue_run_with_job_id_uses_caller_created_binding() -> None:
    from fitcv_cp.queue import enqueue_run_with_job_id

    mock_q = MagicMock()
    mock_q.fetch_job.return_value = None
    mock_job = MagicMock()
    mock_job.id = "run:fixed"
    mock_q.enqueue.return_value = mock_job
    with patch("fitcv_cp.queue.get_queue", return_value=mock_q), patch.dict(
        "os.environ", {"FITCV_CP_INLINE_EXECUTION": "0"}
    ):
        run_id, job_id = enqueue_run_with_job_id(
            jobs_path="data/jobs.json",
            config_path=".env.yaml",
            triggered_by="admin",
            queue_job_id="run:fixed",
        )

    assert job_id == "run:fixed"
    assert mock_q.enqueue.call_args.kwargs["job_id"] == "run:fixed"


def test_enqueue_scan_uses_stable_queue_job_id() -> None:
    mock_q = MagicMock()
    mock_q.enqueue.return_value.id = "scan:scan-123"
    with patch("fitcv_cp.queue.get_queue", return_value=mock_q):
        with patch.dict("os.environ", {"FITCV_CP_INLINE_EXECUTION": "0"}):
            from fitcv_cp.queue import enqueue_scan_with_job_id

            assert enqueue_scan_with_job_id("scan-123") == "scan:scan-123"
    assert mock_q.enqueue.call_args.kwargs["job_id"] == "scan:scan-123"

def test_enqueue_scan_inline_uses_local_executor() -> None:
    from fitcv_cp.queue import enqueue_scan_with_job_id

    executor = MagicMock()
    with patch("fitcv_cp.local_app.get_local_job_executor", return_value=executor), patch(
        "fitcv_cp.sqlite_store.get_scan_queue_job_id", return_value=None
    ), patch("fitcv_cp.sqlite_store.bind_scan_queue_job"), patch.dict(
        "os.environ", {"FITCV_CP_INLINE_EXECUTION": "1"}, clear=False
    ):
        queue_job_id = enqueue_scan_with_job_id("scan-inline-123")

    assert queue_job_id == "scan:scan-inline-123"
    executor.submit.assert_called_once()


def test_enqueue_candidate_profile_stage_uses_stable_rq_target() -> None:
    mock_q = MagicMock()
    mock_q.enqueue.return_value.id = "candidate-profile-attempt-1-base_mapping-claim-1"
    with patch("fitcv_cp.queue.get_queue", return_value=mock_q), patch.dict(
        "os.environ", {"FITCV_CP_INLINE_EXECUTION": "0"}
    ):
        job_id = queue_module.enqueue_candidate_profile_stage(
            attempt_id="attempt-1",
            stage="base_mapping",
            claim_id="claim-1",
            expected_revision=2,
            targets=None,
        )

    assert job_id == "candidate-profile-attempt-1-base_mapping-claim-1"
    call = mock_q.enqueue.call_args
    assert call.args[0].__name__ == "execute_candidate_profile_stage"
    assert call.kwargs["attempt_id"] == "attempt-1"
    assert call.kwargs["job_id"] == job_id


def test_enqueue_run_with_job_id_wires_fixed_rq_retry_when_attempts_exceed_one() -> None:
    from rq.job import Retry

    from fitcv_cp.queue import enqueue_run_with_job_id

    mock_q = MagicMock()
    mock_job = MagicMock()
    mock_job.id = "rq-job-abc"
    mock_q.enqueue.return_value = mock_job
    from fitcv_cp.retry_settings import RetrySettings

    with patch("fitcv_cp.queue.get_queue", return_value=mock_q):
        with patch.dict("os.environ", {"FITCV_CP_INLINE_EXECUTION": "0"}, clear=False):
            with patch(
                "fitcv_cp.retry_settings.load_retry_settings",
                return_value=RetrySettings(
                    maximum_attempts=3,
                    initial_backoff_seconds=10,
                    lease_seconds=900,
                    reconciler_interval_seconds=30,
                    error_detail_limit=2048,
                ),
            ):
                _run_id, _job_id = enqueue_run_with_job_id(
                    jobs_path="data/jobs.json",
                    config_path=".env.yaml",
                    triggered_by="admin",
                    redis_url="redis://localhost:6379/0",
                )

    _fn, _args, kwargs = mock_q.enqueue.mock_calls[0]
    assert isinstance(kwargs.get("retry"), Retry)
    assert kwargs["retry"].max == 2
    assert kwargs["retry"].intervals == [10]
    assert "attempt_id" not in kwargs


def test_enqueue_run_still_returns_str():
    """Existing enqueue_run() keeps returning a plain str (backward compat)."""
    from fitcv_cp.queue import enqueue_run
    mock_q = MagicMock()
    mock_job = MagicMock()
    mock_job.id = "rq-job-xyz"
    mock_q.enqueue.return_value = mock_job
    with patch("fitcv_cp.queue.get_queue", return_value=mock_q):
        with patch.dict("os.environ", {"FITCV_CP_INLINE_EXECUTION": "0"}):
            result = enqueue_run(
                jobs_path="data/jobs.json",
                config_path=".env.yaml",
                triggered_by="admin",
                redis_url="redis://localhost:6379/0",
            )
    assert isinstance(result, str) and len(result) == 36

def test_enqueue_cv_regenerate_once_with_job_id_returns_job_id() -> None:
    from fitcv_cp.queue import enqueue_cv_regenerate_once_with_job_id

    mock_q = MagicMock()
    mock_job = MagicMock()
    mock_job.id = "rq-regenerate-1"
    mock_q.enqueue.return_value = mock_job
    with patch("fitcv_cp.queue.get_queue", return_value=mock_q):
        with patch.dict("os.environ", {"FITCV_CP_INLINE_EXECUTION": "0"}):
            queue_job_id = enqueue_cv_regenerate_once_with_job_id(
                run_id="run-1",
                job_url="https://example.com/job",
                actor="admin",
                note="retry",
                cv_version_id="cv-2",
                parent_cv_version_id="cv-1",
                idempotency_key="regen-1",
                action_id="action-1",
                redis_url="redis://localhost:6379/0",
            )
    assert queue_job_id == "rq-regenerate-1"
    assert mock_q.enqueue.call_args.kwargs["cv_version_id"] == "cv-2"
    assert mock_q.enqueue.call_args.kwargs["parent_cv_version_id"] == "cv-1"
    assert mock_q.enqueue.call_args.kwargs["idempotency_key"] == "regen-1"
    assert mock_q.enqueue.call_args.kwargs["action_id"] == "action-1"

def test_enqueue_cv_regenerate_once_with_job_id_inline_marks_queued() -> None:
    from fitcv_cp.queue import enqueue_cv_regenerate_once_with_job_id

    with patch("fitcv_cp.queue.threading.Thread") as thread_cls:
        thread = MagicMock()
        thread_cls.return_value = thread
        with patch.dict("os.environ", {"FITCV_CP_INLINE_EXECUTION": "1"}):
            queue_job_id = enqueue_cv_regenerate_once_with_job_id(
                run_id="run-2",
                job_url="https://example.com/job2",
                actor="admin",
                note=None,
            )
    assert queue_job_id.startswith("inline-")
    assert queue_module._INLINE_JOB_STATUS[queue_job_id] == "queued"
    thread.start.assert_called_once()


def test_packaged_inline_enqueue_uses_process_executor_not_thread() -> None:
    from fitcv_cp.queue import enqueue_cv_regenerate_once_with_job_id

    executor = MagicMock()
    with patch("fitcv_cp.local_app.get_local_job_executor", return_value=executor), patch(
        "fitcv_cp.queue.threading.Thread"
    ) as thread_cls, patch("fitcv_cp.queue.get_queue") as get_queue, patch.dict(
        "os.environ",
        {"FITCV_CP_INLINE_EXECUTION": "1", "FITCV_LOCAL_MODE": "1"},
        clear=False,
    ):
        queue_job_id = enqueue_cv_regenerate_once_with_job_id(
            run_id="run-local",
            job_url="https://example.com/job",
            actor="admin",
        )

    assert queue_job_id.startswith("inline-")
    executor.submit.assert_called_once()
    thread_cls.assert_not_called()
    get_queue.assert_not_called()


# ── cancel_queued_run ────────────────────────────────────────────────────────

def test_cancel_queued_run_returns_true_when_cancelable():
    """@proves admin_control_plane_core.rq-background-worker-integration
    @proves run_lifecycle_controls.cancel-queued-runs-directly-from-the-queue-via-rq
    @proves trigger_run_management.manual-checkpoints-and-continue
    @proves trigger_run_management.run-detail-actions
    """
    from fitcv_cp.queue import cancel_queued_run
    mock_job = MagicMock()
    with patch("fitcv_cp.queue.Job.fetch", return_value=mock_job):
        result = cancel_queued_run("rq-job-abc", redis_url="redis://localhost:6379/0")
    assert result is True
    mock_job.cancel.assert_called_once()


def test_cancel_queued_run_returns_false_when_not_found():
    """@proves run_lifecycle_controls.cancel-queued-runs-directly-from-the-queue-via-rq
    @proves trigger_run_management.manual-checkpoints-and-continue
    """
    from fitcv_cp.queue import cancel_queued_run
    from rq.exceptions import NoSuchJobError
    with patch("fitcv_cp.queue.Job.fetch", side_effect=NoSuchJobError("rq-job-missing")):
        result = cancel_queued_run("rq-job-missing", redis_url="redis://localhost:6379/0")
    assert result is False


def test_inline_start_delay_seconds_bounds_values() -> None:
    with patch.dict("os.environ", {"FITCV_CP_INLINE_START_DELAY_SECONDS": "0.2"}, clear=False):
        assert queue_module._inline_start_delay_seconds() == 0.2
    with patch.dict("os.environ", {"FITCV_CP_INLINE_START_DELAY_SECONDS": "-4"}, clear=False):
        assert queue_module._inline_start_delay_seconds() == 0.0
    with patch.dict("os.environ", {"FITCV_CP_INLINE_START_DELAY_SECONDS": "bogus"}, clear=False):
        assert queue_module._inline_start_delay_seconds() == 0.05


def test_run_inline_job_after_delay_waits_before_execution() -> None:
    with patch("fitcv_cp.queue.time.sleep") as sleep_mock:
        with patch("fitcv_cp.queue._run_inline_job") as run_mock:
            with patch.dict("os.environ", {"FITCV_CP_INLINE_START_DELAY_SECONDS": "0.25"}, clear=False):
                queue_module._run_inline_job_after_delay(
                    "inline-job-1",
                    "run-1",
                    "data/jobs.json",
                    ".env.yaml",
                )
    sleep_mock.assert_called_once_with(0.25)
    run_mock.assert_called_once_with(
        "inline-job-1",
        "run-1",
        "data/jobs.json",
        ".env.yaml",
    )


def test_run_inline_job_retries_with_same_scalar_backoff() -> None:
    from fitcv_cp.retry_settings import RetrySettings

    with patch(
        "fitcv_cp.retry_settings.load_retry_settings",
        return_value=RetrySettings(
            maximum_attempts=3,
            initial_backoff_seconds=7,
            lease_seconds=300,
            reconciler_interval_seconds=30,
            error_detail_limit=10000,
        ),
    ), patch(
        "fitcv_cp.worker_job.execute_pipeline_run",
        side_effect=[RuntimeError("one"), RuntimeError("two"), None],
    ) as execute, patch("fitcv_cp.queue.time.sleep") as sleep:
        queue_module._run_inline_job(
            "inline-retry",
            "run-retry",
            "data/jobs.json",
            ".env.yaml",
        )

    assert execute.call_count == 3
    assert [call.args for call in sleep.call_args_list] == [(7,), (7,)]
    assert queue_module._INLINE_JOB_STATUS["inline-retry"] == "finished"


def test_get_queue_job_status_normalizes_rq_runtime_values() -> None:
    from fitcv_cp.queue import get_queue_job_status

    mock_job = MagicMock()
    mock_job.get_status.return_value = "running"
    with patch("fitcv_cp.queue.Job.fetch", return_value=mock_job):
        assert get_queue_job_status("rq-job-1", redis_url="redis://localhost:6379/0") == "started"


def test_get_queue_job_status_normalizes_inline_missing_run() -> None:
    from fitcv_cp.queue import get_queue_job_status

    queue_module._INLINE_JOB_STATUS["inline-1"] = "missing_run"
    assert get_queue_job_status("inline-1") == "missing"



def test_enqueue_run_with_job_id_does_not_wire_rq_retry_for_one_attempt() -> None:
    from fitcv_cp.queue import enqueue_run_with_job_id

    mock_q = MagicMock()
    mock_job = MagicMock()
    mock_job.id = "rq-job-abc"
    mock_q.enqueue.return_value = mock_job

    from fitcv_cp.retry_settings import RetrySettings

    with patch("fitcv_cp.queue.get_queue", return_value=mock_q):
        with patch.dict("os.environ", {"FITCV_CP_INLINE_EXECUTION": "0"}, clear=False):
            with patch(
                "fitcv_cp.retry_settings.load_retry_settings",
                return_value=RetrySettings(
                    maximum_attempts=1,
                    initial_backoff_seconds=10,
                    lease_seconds=900,
                    reconciler_interval_seconds=30,
                    error_detail_limit=2048,
                ),
            ):
                _run_id, _job_id = enqueue_run_with_job_id(
                    jobs_path="data/jobs.json",
                    config_path=".env.yaml",
                    triggered_by="admin",
                    redis_url="redis://localhost:6379/0",
                )

    _fn, _args, kwargs = mock_q.enqueue.mock_calls[0]
    assert kwargs.get("retry") is None
