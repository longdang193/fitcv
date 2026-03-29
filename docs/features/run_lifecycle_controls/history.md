# Run Lifecycle Controls — History

## Changelog

### 1.0.0 — active

- Cancel queued runs via RQ (`cancel_queued_run` in `queue.py`)
- Cooperative cancellation: `_cancellation_check` callback in `worker_job.py`, 3 checkpoints in `pipeline.py` (before enrichment, AI scoring, CV generation)
- `PipelineCancelled` exception for clean mid-flight abort
- Stale cancellation repair endpoint (`/admin/runs/{run_id}/repair-cancellation`)
- Archive and unarchive terminal runs with audit trail in `pipeline_run_events`
- Full test coverage: 12+ tests in `test_app.py` covering cancel, archive, unarchive, repair, and filter scenarios

### 0.4.0 — building

- Archive and unarchive terminal runs
- Stale cancellation repair endpoint
- Spec/plan: `docs/superpowers/specs/2026-03-26-run-lifecycle-controls-design.md`

## Post-Execution Review

- All capabilities from the contract are implemented and tested
- Cooperative cancellation pattern checks BigQuery for `cancel_requested_at` at each checkpoint
- Three-tier stop logic: queue cancel → pre-claim cancel → cooperative cancelling
