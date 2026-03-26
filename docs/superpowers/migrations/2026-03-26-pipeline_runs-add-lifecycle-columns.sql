-- Migration: add run lifecycle columns to pipeline_runs
-- Apply this BEFORE deploying lifecycle-control code.
-- Safe to re-run: ADD COLUMN IF NOT EXISTS is idempotent.

ALTER TABLE `{project}.{dataset}.pipeline_runs`
  ADD COLUMN IF NOT EXISTS queue_job_id         STRING,
  ADD COLUMN IF NOT EXISTS cancel_requested_at  TIMESTAMP,
  ADD COLUMN IF NOT EXISTS cancel_requested_by  STRING,
  ADD COLUMN IF NOT EXISTS archived_at          TIMESTAMP,
  ADD COLUMN IF NOT EXISTS archived_by          STRING;
