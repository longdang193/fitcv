"""
@meta
name: fitcv_cp_orchestrator
type: utility
domain: run_orchestration
responsibility:
  - Provide orchestration adapter boundary for run lifecycle actions.
  - Keep default queue-backed orchestration behavior stable.
inputs:
  - jobs paths, config paths, and run identifiers
  - redis connection settings
outputs:
  - queued run submissions and queue cancellation outcomes
capabilities:
  - trigger_run_management.runs-list-management
  - trigger_run_management.run-detail-actions
  - run_lifecycle_controls.cancel-queued-runs-directly-from-the-queue-via-rq
tags:
  - orchestration
  - adapter
lifecycle:
  status: active
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from fitcv_cp import queue


@dataclass(frozen=True)
class RunSubmission:
    run_id: str
    queue_job_id: str
    backend_run_id: str | None = None
    backend: str = "queue"


OrchestrationMode = Literal["default_queue", "prefect"]


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
        run_id_value, queue_job_id = queue.enqueue_run_with_job_id(
            jobs_path=jobs_path,
            config_path=config_path,
            triggered_by=triggered_by,
            redis_url=redis_url,
            run_id=run_id,
        )
        return RunSubmission(
            run_id=run_id_value,
            queue_job_id=queue_job_id,
            backend_run_id=queue_job_id,
            backend="queue",
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
        return queue.get_queue_job_status(queue_job_id=queue_job_id, redis_url=redis_url)


@dataclass(frozen=True)
class PrefectOrchestrationAdapter(OrchestrationAdapter):
    """Prefect-mode adapter with safe queue fallback while Prefect rollout matures."""

    def submit(
        self,
        *,
        jobs_path: str,
        config_path: str,
        triggered_by: str,
        redis_url: str,
        run_id: str | None = None,
    ) -> RunSubmission:
        # Phase 2 bridge: keep runtime semantics stable by delegating execution to
        # existing queue worker path while exposing a dedicated Prefect adapter mode.
        submission = super().submit(
            jobs_path=jobs_path,
            config_path=config_path,
            triggered_by=triggered_by,
            redis_url=redis_url,
            run_id=run_id,
        )
        return RunSubmission(
            run_id=submission.run_id,
            queue_job_id=submission.queue_job_id,
            backend_run_id=submission.backend_run_id,
            backend="prefect",
        )


def get_orchestration_adapter() -> OrchestrationAdapter:
    """Resolve orchestration adapter from runtime mode, defaulting to queue."""
    mode = str(os.environ.get("FITCV_ORCHESTRATION_MODE", "default_queue") or "default_queue").strip().lower()
    if mode == "prefect":
        return PrefectOrchestrationAdapter(name="prefect")
    return OrchestrationAdapter(name="default_queue")
