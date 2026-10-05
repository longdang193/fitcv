-- Read-only analytical views. Operational SQLite remains source of truth.
-- Grain: one row per run_job_id + artifact_version_id for gold_cv_effort.
CREATE VIEW IF NOT EXISTS gold_cv_effort AS
SELECT run_job_id, artifact_version_id, accepted_at, source_observation_id
FROM silver_cv_artifact
WHERE acceptance_state = 'accepted';

-- Grain: one row per evidence_id for gold_acceptance_state.
CREATE VIEW IF NOT EXISTS gold_acceptance_state AS
SELECT evidence_id, claim, status, cohort_id, cohort_type,
       source_commit, declared_input_fingerprint, material_metrics_sha256
FROM silver_acceptance_evidence;
