/* @bruin

type: bq.table
name: fitcv.run_structured_jobs
description: "Immutable, run-scoped enrichment outputs. One row per run_id + job_url. Append-only — never updated in place. Used for per-run debugging and inspection of what enrichment produced for a specific pipeline run."

columns:
  - name: run_id
    description: "Pipeline run identifier — FK to pipeline_runs.run_id"
  - name: job_url
    description: "LinkedIn job URL — part of logical composite key"
  - name: location_type
    description: "LLM-enriched: canonical remote / hybrid / onsite (lowercase only)"
  - name: seniority
    description: "LLM-enriched: normalized level from JD text — junior / mid / senior / lead"
  - name: domain
    description: "LLM-enriched: business/industry domain (e.g. banking, fintech, healthcare)"
  - name: job_family
    description: "LLM-enriched: role category (e.g. data_engineering, analytics, data_science)"
  - name: enrichment_version
    description: "Prompt/schema version used for this enrichment (e.g. v1)"
  - name: enrichment_model
    description: "Model name used for extraction (e.g. gemini-2.0-flash)"

@bruin */

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.run_structured_jobs` (
  run_id               STRING    NOT NULL  OPTIONS (description = "Pipeline run identifier — part of logical composite PK"),
  job_url              STRING    NOT NULL  OPTIONS (description = "LinkedIn job URL — part of logical composite PK"),
  title                STRING              OPTIONS (description = "Job title"),
  company_name         STRING              OPTIONS (description = "Company display name"),
  location             STRING              OPTIONS (description = "Free-text location string"),
  contract_type        STRING              OPTIONS (description = "Full-time / Part-time / Internship / Contract"),
  experience_level     STRING              OPTIONS (description = "Raw LinkedIn label — NOT the same as enriched seniority"),
  published_at         DATE                OPTIONS (description = "ISO date the job was published"),
  location_type        STRING              OPTIONS (description = "LLM: remote / hybrid / onsite"),
  seniority            STRING              OPTIONS (description = "LLM: junior / mid / senior / lead — inferred from JD text"),
  required_skills      ARRAY<STRING>       OPTIONS (description = "LLM-extracted required skills"),
  preferred_skills     ARRAY<STRING>       OPTIONS (description = "LLM-extracted preferred/nice-to-have skills"),
  responsibilities     ARRAY<STRING>       OPTIONS (description = "LLM-extracted responsibilities"),
  domain               STRING              OPTIONS (description = "LLM: business/industry domain"),
  tech_stack           ARRAY<STRING>       OPTIONS (description = "LLM-extracted technologies"),
  years_experience_min INT64               OPTIONS (description = "LLM-extracted minimum years required"),
  years_experience_max INT64               OPTIONS (description = "LLM-extracted maximum years mentioned"),
  keywords             ARRAY<STRING>       OPTIONS (description = "LLM-extracted searchable keywords"),
  job_family           STRING              OPTIONS (description = "LLM: role category — data_engineering / analytics / data_science / ml_engineering"),
  description_cleaned  STRING              OPTIONS (description = "Whitespace-normalized description text"),
  enrichment_version   STRING              OPTIONS (description = "Prompt/schema version, e.g. v1"),
  enrichment_model     STRING              OPTIONS (description = "Model name used, e.g. gemini-2.0-flash"),
  enriched_at          TIMESTAMP           OPTIONS (description = "Enrichment timestamp")
)
OPTIONS (
  description = "Immutable run-scoped enrichment outputs — one row per run_id + job_url, append-only"
);
