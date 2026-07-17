"""@meta
name: orchestrator
type: module
domain: runtime
ownership: infrastructure
responsibility:
  - Module metadata placeholder for src.fitcv_cp.orchestrator.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError

from fitcv_cp import queue
from fitcv_cp.runtime_contracts import normalize_orchestration_status


@dataclass(frozen=True, init=False)
class RunSubmission:
    run_id: str
    queue_job_id: str
    backend_run_id: str | None = None
    requested_backend: str = "queue"
    execution_backend: str = "queue"

    def __init__(
        self,
        *,
        run_id: str,
        queue_job_id: str,
        backend_run_id: str | None = None,
        requested_backend: str = "queue",
        execution_backend: str = "queue",
        backend: str | None = None,
    ) -> None:
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "queue_job_id", queue_job_id)
        object.__setattr__(self, "backend_run_id", backend_run_id)
        object.__setattr__(self, "requested_backend", requested_backend)
        resolved_backend = str(backend).strip() if backend is not None else ""
        object.__setattr__(self, "execution_backend", resolved_backend or execution_backend)

    @property
    def backend(self) -> str:
        """Backward-compatible alias retained for existing callers/tests."""
        return self.execution_backend


OrchestrationMode = Literal["default_queue"]


@dataclass(frozen=True)
class OrchestrationAdapter:
    name: OrchestrationMode

    def enqueue_run_with_job_id(
        self,
        *,
        jobs_path: str,
        config_path: str,
        triggered_by: str,
        redis_url: str,
        run_id: str | None = None,
    ) -> tuple[str, str]:
        submission = self.submit(
            jobs_path=jobs_path,
            config_path=config_path,
            triggered_by=triggered_by,
            redis_url=redis_url,
            run_id=run_id,
        )
        return submission.run_id, submission.queue_job_id

    def enqueue_run(
        self,
        *,
        jobs_path: str,
        config_path: str,
        triggered_by: str,
        redis_url: str,
        run_id: str | None = None,
    ) -> str:
        submission = self.submit(
            jobs_path=jobs_path,
            config_path=config_path,
            triggered_by=triggered_by,
            redis_url=redis_url,
            run_id=run_id,
        )
        return submission.run_id

    def cancel_queued_run(self, *, queue_job_id: str, redis_url: str) -> bool:
        return self.cancel(queue_job_id=queue_job_id, redis_url=redis_url)

    def submit(
        self,
        *,
        jobs_path: str,
        config_path: str,
        triggered_by: str,
        redis_url: str,
        run_id: str | None = None,
    ) -> RunSubmission:
        try:
            run_id_value, queue_job_id = queue.enqueue_run_with_job_id(
                jobs_path=jobs_path,
                config_path=config_path,
                triggered_by=triggered_by,
                redis_url=redis_url,
                run_id=run_id,
            )
        except RedisConnectionError as exc:
            raise HTTPException(status_code=503, detail="Queue backend unavailable") from exc
        return RunSubmission(
            run_id=run_id_value,
            queue_job_id=queue_job_id,
            backend_run_id=queue_job_id,
            requested_backend=self.name,
            execution_backend="queue",
        )

    def continue_run(
        self,
        *,
        run_id: str,
        jobs_path: str,
        config_path: str,
        triggered_by: str,
        redis_url: str,
    ) -> RunSubmission:
        # Continue uses the same bounded execution submit path with a fixed run_id.
        return self.submit(
            jobs_path=jobs_path,
            config_path=config_path,
            triggered_by=triggered_by,
            redis_url=redis_url,
            run_id=run_id,
        )

    def cancel(self, *, queue_job_id: str, redis_url: str) -> bool:
        return queue.cancel_queued_run(queue_job_id=queue_job_id, redis_url=redis_url)

    def status(self, *, queue_job_id: str, redis_url: str) -> str:
        return normalize_orchestration_status(
            queue.get_queue_job_status(queue_job_id=queue_job_id, redis_url=redis_url)
        )


def get_orchestration_adapter() -> OrchestrationAdapter:
    """Return the single supported queue orchestration adapter."""
    return OrchestrationAdapter(name="default_queue")
