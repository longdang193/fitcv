"""RQ queue setup for background pipeline execution."""
import uuid
from typing import Optional

import redis
from rq import Queue
from rq.job import Job

_queue: Optional[Queue] = None


def get_queue(redis_url: str = "redis://redis:6379/0") -> Queue:
    global _queue
    if _queue is None:
        conn = redis.from_url(redis_url)
        _queue = Queue("fitcv", connection=conn)
    return _queue


def enqueue_run_with_job_id(
    jobs_path: str,
    config_path: str,
    triggered_by: str,
    redis_url: str = "redis://redis:6379/0",
    run_id: Optional[str] = None,
) -> tuple[str, str]:
    """Enqueue a pipeline run. Returns (run_id, rq_job_id)."""
    from fitcv_cp import worker_job  # noqa: F401

    if run_id is None:
        run_id = str(uuid.uuid4())
    q = get_queue(redis_url)
    job = q.enqueue(
        worker_job.execute_pipeline_run,
        run_id=run_id,
        jobs_path=jobs_path,
        config_path=config_path,
        job_timeout=3600,
    )
    return run_id, job.id


def enqueue_run(
    jobs_path: str,
    config_path: str,
    triggered_by: str,
    redis_url: str = "redis://redis:6379/0",
    run_id: Optional[str] = None,
) -> str:
    """Enqueue a pipeline run. Returns the run_id (backward-compatible wrapper)."""
    run_id, _job_id = enqueue_run_with_job_id(
        jobs_path=jobs_path,
        config_path=config_path,
        triggered_by=triggered_by,
        redis_url=redis_url,
        run_id=run_id,
    )
    return run_id


def cancel_queued_run(queue_job_id: str, redis_url: str = "redis://redis:6379/0") -> bool:
    """Attempt to cancel a queued RQ job before the worker claims it.

    Returns True if the job was successfully cancelled/removed.
    Returns False if the job was already claimed, missing, or not cancelable.
    """
    from rq.exceptions import NoSuchJobError

    conn = redis.from_url(redis_url)
    try:
        job = Job.fetch(queue_job_id, connection=conn)
        job.cancel()
        return True
    except (NoSuchJobError, Exception):
        return False
