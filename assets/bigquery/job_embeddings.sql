/* @bruin

type: bq.table
name: fitcv.job_embeddings
description: "Semantic embeddings for job postings. v1: one row per job (chunk_type = job_summary) used for VECTOR_SEARCH shortlist ranking."

columns:
  - name: job_url
    description: "FK to fitcv.structured_jobs.job_url"
  - name: chunk_type
    description: "v1: always job_summary. Future: responsibilities, required_skills, etc."
  - name: chunk_text
    description: "The labelled-section text that was embedded"
  - name: embedding
    description: "Dense vector from Vertex AI text-embedding-005"

@bruin */

CREATE TABLE IF NOT EXISTS fitcv.job_embeddings (
  job_url    STRING         NOT NULL  OPTIONS (description = "FK → structured_jobs.job_url"),
  chunk_type STRING                   OPTIONS (description = "v1: always job_summary"),
  chunk_text STRING                   OPTIONS (description = "Labelled-section text that was embedded"),
  embedding  ARRAY<FLOAT64>           OPTIONS (description = "Dense vector from Vertex AI text-embedding-005"),
  created_at TIMESTAMP
)
OPTIONS (description = "Job posting semantic embeddings — one summary vector per job in v1");
