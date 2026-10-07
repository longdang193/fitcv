-- Disposable analytical projection views. Operational SQLite remains source of truth.
DROP VIEW IF EXISTS gold_cv_artifact;
CREATE VIEW gold_cv_artifact AS
SELECT json_extract(payload_json, '$.run_job_id') AS run_job_id,
       json_extract(payload_json, '$.artifact_id') AS artifact_id,
       json_extract(payload_json, '$.accepted_at') AS accepted_at,
       payload_json
FROM silver_cv_artifact;

DROP VIEW IF EXISTS gold_run_job_effort;
CREATE VIEW gold_run_job_effort AS
SELECT json_extract(payload_json, '$.run_job_id') AS run_job_id,
       json_extract(payload_json, '$.cohort_id') AS cohort_id,
       json_extract(payload_json, '$.accepted_artifact_count') AS accepted_artifact_count,
       json_extract(payload_json, '$.provider_call_count') AS provider_call_count,
       json_extract(payload_json, '$.token_total') AS token_total,
       payload_json
FROM silver_run_job_effort;

DROP VIEW IF EXISTS gold_cohort_effort;
CREATE VIEW gold_cohort_effort AS
SELECT json_extract(payload_json, '$.cohort_id') AS cohort_id,
       json_extract(payload_json, '$.cohort_type') AS cohort_type,
       json_extract(payload_json, '$.attempted_job_count') AS attempted_job_count,
       json_extract(payload_json, '$.accepted_artifact_count') AS accepted_artifact_count,
       json_extract(payload_json, '$.provider_call_count') AS provider_call_count,
       json_extract(payload_json, '$.token_total') AS token_total,
       payload_json
FROM silver_cohort_effort;

DROP VIEW IF EXISTS gold_requirement_demand;
CREATE VIEW gold_requirement_demand AS
SELECT json_extract(payload_json, '$.requirement') AS requirement,
       json_extract(payload_json, '$.cohort_id') AS cohort_id,
       json_extract(payload_json, '$.cohort_type') AS cohort_type,
       json_extract(payload_json, '$.numerator_posting_count') AS numerator_posting_count,
       json_extract(payload_json, '$.denominator_posting_count') AS denominator_posting_count,
       payload_json
FROM silver_requirement_demand;

DROP VIEW IF EXISTS gold_candidate_gap;
CREATE VIEW gold_candidate_gap AS
SELECT json_extract(payload_json, '$.requirement') AS requirement,
       json_extract(payload_json, '$.gap_category') AS gap_category,
       json_extract(payload_json, '$.cohort_id') AS cohort_id,
       json_extract(payload_json, '$.cohort_type') AS cohort_type,
       json_extract(payload_json, '$.numerator_requirement_count') AS numerator_requirement_count,
       json_extract(payload_json, '$.denominator_requirement_count') AS denominator_requirement_count,
       payload_json
FROM silver_candidate_gap;

DROP VIEW IF EXISTS gold_acceptance_state;
CREATE VIEW gold_acceptance_state AS
SELECT json_extract(payload_json, '$.row_key') AS row_key,
       json_extract(payload_json, '$.priority') AS priority,
       json_extract(payload_json, '$.evidence_id') AS evidence_id,
       json_extract(payload_json, '$.evidence_status') AS evidence_status,
       json_extract(payload_json, '$.implementation_status') AS implementation_status,
       json_extract(payload_json, '$.acceptance_status') AS acceptance_status,
       json_extract(payload_json, '$.measurement_status') AS measurement_status,
       payload_json
FROM silver_acceptance_evidence;

DROP VIEW IF EXISTS gold_optimization_state;
CREATE VIEW gold_optimization_state AS
SELECT json_extract(payload_json, '$.row_key') AS row_key,
       json_extract(payload_json, '$.priority') AS priority,
       json_extract(payload_json, '$.evidence_id') AS evidence_id,
       json_extract(payload_json, '$.measurement_status') AS measurement_status,
       json_extract(payload_json, '$.optimization_status') AS optimization_status,
       json_extract(payload_json, '$.optimization_experiment') AS optimization_experiment,
       json_extract(payload_json, '$.optimization_promotion') AS optimization_promotion,
       json_extract(payload_json, '$.optimization_production_default') AS optimization_production_default,
       json_extract(payload_json, '$.optimization_evidence') AS optimization_evidence,
       payload_json
FROM silver_optimization_state;

DROP VIEW IF EXISTS gold_semantic_metric;
CREATE VIEW gold_semantic_metric AS
SELECT json_extract(payload_json, '$.metric_id') AS metric_id,
       json_extract(payload_json, '$.metric_version') AS metric_version,
       json_extract(payload_json, '$.cohort_id') AS cohort_id,
       json_extract(payload_json, '$.cohort_type') AS cohort_type,
       json_extract(payload_json, '$.dimension_key') AS dimension_key,
       json_extract(payload_json, '$.numerator') AS numerator,
       json_extract(payload_json, '$.denominator') AS denominator,
       json_extract(payload_json, '$.value') AS value,
       json_extract(payload_json, '$.coverage_status') AS coverage_status,
       json_extract(payload_json, '$.coverage_numerator') AS coverage_numerator,
       json_extract(payload_json, '$.coverage_denominator') AS coverage_denominator,
       json_extract(payload_json, '$.unavailable_reason') AS unavailable_reason,
       json_extract(payload_json, '$.source_commit') AS source_commit,
       json_extract(payload_json, '$.input_fingerprint') AS input_fingerprint,
       json_extract(payload_json, '$.material_digest') AS material_digest,
       payload_json
FROM gold_semantic_metric_rows;
