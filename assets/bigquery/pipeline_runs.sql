CREATE TABLE IF NOT EXISTS `{project}.{dataset}.pipeline_runs` (
  run_id          STRING    NOT NULL OPTIONS(description="UUID4 run identifier"),
  status          STRING    NOT NULL OPTIONS(description="queued | running | succeeded | failed"),
  triggered_by    STRING,
  trigger_source  STRING,
  jobs_path       STRING,
  config_path     STRING,
  created_at      TIMESTAMP NOT NULL,
  started_at      TIMESTAMP,
  finished_at     TIMESTAMP,
  total_jobs      INT64,
  passed_filter   INT64,
  ranked          INT64,
  cvs_generated   INT64,
  error_message   STRING,
  error_stage     STRING    OPTIONS(description="stage name where the run failed")
);
