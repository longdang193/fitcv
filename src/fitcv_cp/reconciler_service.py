"""@meta
name: reconciler_service
type: module
domain: run_orchestration
ownership: infrastructure
responsibility:
  - Provide dedicated reconciler process for abandoned attempt recovery.
inputs:
  - canonical System settings (reconciler_interval_seconds)
  - backend runtime (SQLite)
outputs:
  - periodic reconcile_abandoned_attempts() side effects
lifecycle:
  - status: active
"""

from __future__ import annotations

import datetime
import logging
import time

from fitcv_cp.backend_runtime import resolve_backend_runtime
from fitcv_cp.reconciler import reconcile_abandoned_attempts
from fitcv_cp.retry_settings import load_retry_settings
from fitcv_cp.store import ControlPlaneStore

logger = logging.getLogger(__name__)


def _build_store() -> ControlPlaneStore:
    runtime = resolve_backend_runtime()
    return ControlPlaneStore(backend_runtime=runtime)


def run_reconciler_forever() -> None:
    store = _build_store()
    logger.info("reconciler started")

    while True:
        interval = int(load_retry_settings().reconciler_interval_seconds)
        started_at = datetime.datetime.now(datetime.timezone.utc)
        try:
            summary = reconcile_abandoned_attempts(store, now=started_at)
            logger.info(
                "reconcile summary scanned_runs=%s abandoned_attempts=%s requeued_attempts=%s terminal_failed_runs=%s candidate_profile_abandoned_attempts=%s candidate_profile_purged_sources=%s",
                summary.scanned_runs,
                summary.abandoned_attempts,
                summary.requeued_attempts,
                summary.terminal_failed_runs,
                summary.candidate_profile_abandoned_attempts,
                summary.candidate_profile_purged_sources,
            )
        except Exception as exc:
            logger.exception("reconcile failed: %s", exc)
        time.sleep(max(1, interval))


def main() -> None:
    import os

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    run_reconciler_forever()


if __name__ == "__main__":
    main()
