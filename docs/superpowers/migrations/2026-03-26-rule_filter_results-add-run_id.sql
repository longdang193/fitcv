-- Add run_id to rule_filter_results for run-scoped filter inspection
-- Existing rows remain valid with NULL run_id.
ALTER TABLE `{project}.{dataset}.rule_filter_results`
  ADD COLUMN run_id STRING;
