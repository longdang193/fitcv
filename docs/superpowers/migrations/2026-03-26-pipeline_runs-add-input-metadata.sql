-- Add run-scoped input metadata columns to pipeline_runs
-- Run once only: BigQuery ADD COLUMN does not support IF NOT EXISTS.
ALTER TABLE `{project}.{dataset}.pipeline_runs`
  ADD COLUMN jobs_input_source STRING,
  ADD COLUMN jobs_input_json STRING,
  ADD COLUMN candidate_profile_source STRING,
  ADD COLUMN candidate_profile_json STRING;
