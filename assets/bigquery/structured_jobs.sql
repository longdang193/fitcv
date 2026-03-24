/* @bruin

type: bq.table
name: fitcv.structured_jobs
description: "Enriched job postings combining LinkedIn scraper metadata with LLM-extracted structured fields. Upserted on job_url via MERGE."

columns:
  - name: job_url
    description: "LinkedIn job URL — natural primary key (PK)"
  - name: experience_level
    description: "Raw LinkedIn label from scraper (e.g. Entry level). NOT the same as seniority."
  - name: location_type
    description: "LLM-enriched: canonical remote / hybrid / onsite (lowercase only)"
  - name: seniority
    description: "LLM-enriched: normalized level from JD text — junior / mid / senior / lead. Distinct from experience_level."
  - name: domain
    description: "LLM-enriched: business/industry domain (e.g. banking, fintech, healthcare)"
  - name: job_family
    description: "LLM-enriched: role category (e.g. data_engineering, analytics, data_science)"
  - name: enrichment_version
    description: "Prompt/schema version used for this enrichment (e.g. v1)"
  - name: enrichment_model
    description: "Model name used for extraction (e.g. gemini-2.0-flash)"

@bruin */

CREATE TABLE IF NOT EXISTS fitcv.structured_jobs (
  job_url              STRING    NOT NULL  OPTIONS (description = "LinkedIn job URL — natural primary key"),
  title                STRING              OPTIONS (description = "Job title"),
  company_name         STRING              OPTIONS (description = "Company display name"),
  company_id           STRING              OPTIONS (description = "LinkedIn internal company ID"),
  location             STRING              OPTIONS (description = "Free-text location string"),
  contract_type        STRING              OPTIONS (description = "Full-time / Part-time / Internship / Contract"),
  experience_level     STRING              OPTIONS (description = "Raw LinkedIn label — NOT the same as enriched seniority"),
  sector               STRING              OPTIONS (description = "Sector from scraper"),
  salary_min           FLOAT64             OPTIONS (description = "Parsed salary minimum"),
  salary_max           FLOAT64             OPTIONS (description = "Parsed salary maximum"),
  salary_currency      STRING              OPTIONS (description = "ISO currency code"),
  applications_count   INT64               OPTIONS (description = "Parsed applicants integer"),
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
  description = "Enriched job postings — scraper metadata merged with LLM-extracted structured fields"
);
