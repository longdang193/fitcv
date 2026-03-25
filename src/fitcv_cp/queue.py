"""RQ queue setup for background pipeline execution."""
import uuid
from typing import Optional

import redis
from rq import Queue

_queue: Optional[Queue] = None


def get_queue(redis_url: str = "redis://redis:6379/0") -> Queue:
    global _queue
    if _queue is None:
        conn = redis.from_url(redis_url)
        _queue = Queue("fitcv", connection=conn)
    return _queue


def enqueue_run(
    jobs_path: str,
    config_path: str,
    triggered_by: str,
    redis_url: str = "redis://redis:6379/0",
    run_id: Optional[str] = None,
) -> str:
    """Enqueue a pipeline run. Returns the run_id (UUID4 string)."""
    # Import here to avoid circular deps at module load and allow test patching
    from fitcv_cp import worker_job  # noqa: F401

    if run_id is None:
        run_id = str(uuid.uuid4())
    q = get_queue(redis_url)
    q.enqueue(
        worker_job.execute_pipeline_run,
        run_id=run_id,
        jobs_path=jobs_path,
        config_path=config_path,
        job_timeout=3600,
    )
    return run_id
