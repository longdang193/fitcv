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

from dataclasses import dataclass

from fitcv_cp import queue


@dataclass(frozen=True)
class OrchestrationAdapter:
    name: str

    def enqueue_run_with_job_id(
        self,
        *,
        jobs_path: str,
        config_path: str,
        triggered_by: str,
        redis_url: str,
        run_id: str | None = None,
    ) -> tuple[str, str]:
        return queue.enqueue_run_with_job_id(
            jobs_path=jobs_path,
            config_path=config_path,
            triggered_by=triggered_by,
            redis_url=redis_url,
            run_id=run_id,
        )

    def enqueue_run(
        self,
        *,
        jobs_path: str,
        config_path: str,
        triggered_by: str,
        redis_url: str,
        run_id: str | None = None,
    ) -> str:
        return queue.enqueue_run(
            jobs_path=jobs_path,
            config_path=config_path,
            triggered_by=triggered_by,
            redis_url=redis_url,
            run_id=run_id,
        )

    def cancel_queued_run(self, *, queue_job_id: str, redis_url: str) -> bool:
        return queue.cancel_queued_run(queue_job_id=queue_job_id, redis_url=redis_url)


def get_orchestration_adapter() -> OrchestrationAdapter:
    """Default adapter seam for current queue-backed orchestration."""
    return OrchestrationAdapter(name="default_queue")

