# FitCV Pipeline — Current Implementation Spec

> Source of truth: the code currently on `main`. This document describes the implemented FitCV pipeline as it exists today, not the historical build checklist that created it.

## Goal

FitCV ingests raw job postings, normalizes and enriches them into structured job records, loads a structured candidate profile, applies deterministic rule filters, retrieves semantically similar jobs, reranks them with Gemini, retrieves supporting evidence, generates tailored CVs, validates those CVs, and stores versioned outputs in BigQuery.

## Current Architecture

The pipeline is organized into four runtime layers:

- Layer 1: job ingest, normalization, enrichment, and storage
- Layer 2: candidate profile loading and storage
- Layer 3: deterministic filtering, embeddings, vector retrieval, AI reranking, and final ranking
- Layer 4: evidence retrieval, gap analysis, CV generation, validation, and CV version persistence

Python orchestration and business logic live in [`src/fitcv`](/workspaces/fitcv/src/fitcv). BigQuery table DDL assets live in [`assets/bigquery`](/workspaces/fitcv/assets/bigquery). Runtime defaults and taxonomy files live in [`config`](/workspaces/fitcv/config).

## Runtime Entry Point

The canonical orchestrator is [`run_pipeline()`](/workspaces/fitcv/src/fitcv/pipeline.py).

Current execution order:

- parse raw jobs from a local JSON file
- normalize raw jobs
- store raw jobs in `raw_jobs`
- enrich normalized jobs with Gemini
- store structured jobs in `structured_jobs`
- load the candidate profile from `config["paths"]["candidate_profile"]`
- store candidate profile tables in BigQuery
- apply rule filters before embeddings
- store rule filter pass/reject results
- embed only rule-passing jobs
- embed the candidate profile
- run BigQuery `VECTOR_SEARCH` over the filtered job universe
- rerank the shortlist with Gemini
- compute deterministic final ranking scores
- retrieve evidence, compute gaps, generate CVs, validate CVs, and store accepted CV versions

`run_pipeline()` returns:

```python
{
    "run_id": str,
    "total_jobs": int,
    "passed_filter": int,
    "ranked": int,
    "cvs_generated": int,
}
```

## Configuration Model

The only supported runtime loader is [`load_config()`](/workspaces/fitcv/src/fitcv/config.py).

Load behavior:

- primary env file candidates:
  - `.env.yaml`
  - legacy fallback `config/env.yaml`
- policy overlays merged after env:
  - `config/taxonomy.yaml`
  - `config/skill_synonyms.yaml`
  - `config/pipeline.yaml`
  - `config/ranking.yaml`

Important invariants:

- env config keys win over policy-file keys on collision
- legacy `config/env.yaml` is still supported for backward compatibility
- legacy `ai_score_model` is normalized to `gemini_model`
- Vertex region is separate from BigQuery location via `vertex_location`

Canonical runtime keys in current use:

- `gcp_project`
- `bigquery_dataset`
- `service_account_key`
- `location`
- `vertex_location`
- `gemini_model`
- `embedding_model`
- `paths.candidate_profile`
- `pipeline.vector_search_top_n`
- `pipeline.ai_score_top_n`
- `pipeline.final_top_n`
- `pipeline.evidence_top_k`
- `ranking_weights`
- `ranking_null_defaults`
- `fit_label_thresholds`
- `application_statuses`

Current default runtime values from [`config/env.yaml`](/workspaces/fitcv/config/env.yaml) and policy files:

- BigQuery location: `US`
- Vertex location: `us-central1`
- Gemini model: `gemini-2.5-flash`
- Embedding model: `text-embedding-005`

## Data Source and Input Contract

The implemented pipeline currently reads local LinkedIn scraper exports from JSON arrays. The primary sample fixture is [`data/sample_jobs.json`](/workspaces/fitcv/data/sample_jobs.json).

The ingest path expects the LinkedIn-style flat job schema, including fields such as:

- `title`
- `location`
- `jobUrl`
- `companyName`
- `description`
- `contractType`
- `experienceLevel`
- `sector`
- `salary`
- `publishedAt`

Raw jobs are persisted with the original JSON payload for auditability.

## Layer 1: Jobs

### Ingest

Implemented in [`ingest.py`](/workspaces/fitcv/src/fitcv/ingest.py).

Current responsibilities:

- load jobs from a local JSON array
- validate minimum LinkedIn field presence
- convert scraper objects into raw BigQuery rows
- preserve original job payload in `raw_json`

### Normalization

Implemented in [`normalize.py`](/workspaces/fitcv/src/fitcv/normalize.py).

Current responsibilities:

- convert camelCase scraper keys to snake_case
- normalize known field shapes used by downstream modules
- produce deterministic structured dicts for enrichment

### Enrichment

Implemented in [`enrich.py`](/workspaces/fitcv/src/fitcv/enrich.py).

Current behavior:

- uses `google.genai`
- retries rate-limit failures including `429 RESOURCE_EXHAUSTED`
- uses exponential backoff for retryable enrichment failures
- writes structured jobs to BigQuery with explicit schema handling

Structured enrichment fields consumed downstream include:

- `required_skills`
- `preferred_skills`
- `seniority`
- `job_family`
- `domain`
- `location_type`
- `contract_type`
- `required_skills`
- `published_at`

The enrichment stage is intentionally tolerant of missing inferred fields. Downstream filters now treat unknown inferred values conservatively instead of auto-rejecting jobs.

## Layer 2: Candidate Profile

Implemented in [`candidate.py`](/workspaces/fitcv/src/fitcv/candidate.py).

Source profile:

- [`data/candidate_profile.yaml`](/workspaces/fitcv/data/candidate_profile.yaml)

Current responsibilities:

- load the structured candidate profile YAML
- flatten profile skills across multiple profile sections
- store profile tables in BigQuery:
  - candidate profile
  - experiences
  - projects
  - skills
  - achievements

`flatten_skills()` is the current source of truth for candidate skill provenance and is reused by validation and CV generation.

## Layer 3: Matching

### Rule Filter

Implemented in [`rule_filter.py`](/workspaces/fitcv/src/fitcv/rule_filter.py).

Current deterministic checks:

- seniority fit via configured ladder
- location type preference
- contract type allow/exclude handling
- raw LinkedIn `experience_level` exclusion
- must-have skills with synonym matching
- job freshness by `published_at`
- domain preference using either `job_family` or `domain`

Current filter contract:

```python
{
    "passed": ["job_url_1", "job_url_2"],
    "rejected": [
        {"job_url": "job_url_3", "reasons": ["contract_type_excluded"]}
    ],
}
```

Important behavior hardening now present:

- unknown `seniority` keeps the job
- unknown `location_type` keeps the job
- unknown `domain` keeps the job
- raw `Entry level` no longer auto-rejects by itself
- profile keys `domains` and `exclude_contract_types` are supported directly

### Embeddings and Vector Retrieval

Implemented in [`embeddings.py`](/workspaces/fitcv/src/fitcv/embeddings.py) and [`vector_search.py`](/workspaces/fitcv/src/fitcv/vector_search.py).

Current retrieval design:

- only rule-passing jobs are embedded
- candidate retrieval uses one deterministic summary string
- BigQuery `VECTOR_SEARCH` runs against job embeddings with `chunk_type = 'job_summary'`
- vector search is restricted to the rule-passing job URL universe

Current guardrails:

- empty embedding batches return immediately
- shortlist results are deduplicated by `job_url`
- vector search does not run if there are no passed job URLs

### AI Reranking

Implemented in [`ai_score.py`](/workspaces/fitcv/src/fitcv/ai_score.py).

Current behavior:

- Gemini reranking is shortlist-only
- prompt requires structured JSON output
- fit labels are `strong`, `stretch`, `skip`
- model access priority:
  - `GEMINI_API_KEY`
  - Vertex AI credentials fallback

Current model default:

- `gemini-2.5-flash`

This replaced the earlier broken Vertex publisher-model path using `gemini-2.0-flash*` for this project.

### Final Ranking

Implemented in [`ranking.py`](/workspaces/fitcv/src/fitcv/ranking.py) and `build_ranking_features()` in [`pipeline.py`](/workspaces/fitcv/src/fitcv/pipeline.py).

Current ranking inputs include:

- `ai_score`
- `must_have_match`
- `vector_similarity`
- `title_relevance`
- `seniority_fit`
- `preference_fit`

`final_score` is deterministic and uses configured weights plus null-default fallbacks.

## Layer 4: Personalization and Output

### Evidence Retrieval

Implemented in [`evidence.py`](/workspaces/fitcv/src/fitcv/evidence.py).

Current behavior:

- scores and ranks candidate evidence items against job required skills
- returns normalized evidence records with stable IDs
- feeds top evidence into CV generation and version metadata

### Gap Analysis

Implemented in [`gap_analysis.py`](/workspaces/fitcv/src/fitcv/gap_analysis.py).

Current behavior:

- computes matched, missing, and partial skill coverage
- feeds `classify_fit()`
- `fit == "skip"` jobs are dropped before CV generation

### CV Generation

Implemented in [`cv_generator.py`](/workspaces/fitcv/src/fitcv/cv_generator.py) and [`templates/cv_template.md`](/workspaces/fitcv/templates/cv_template.md).

Current behavior:

- uses Gemini via `google.genai`
- builds prompt from:
  - job context
  - retrieved evidence
  - gap analysis
  - markdown template
  - candidate profile grounding constraints

Current anti-hallucination prompt constraints:

- do not invent employer names
- do not invent project names
- only use employers and projects from the candidate profile
- in the `Skills` section, only use skills from the candidate skill whitelist

### Validation

Implemented in [`validator.py`](/workspaces/fitcv/src/fitcv/validator.py).

Current validation output schema:

```python
{
    "valid": bool,
    "missing_sections": list[str],
    "grounding_violations": list[str],
    "skill_violations": list[str],
    "warnings": list[str],
}
```

Current checks:

- required section presence
- length warning by estimated page count
- employer grounding
- project existence checks
- skill provenance using flattened candidate skills and synonym-aware canonicalization

Recent validator hardening reflected in current code:

- no longer misreads `Great Expectations` as an employer
- no longer treats every markdown heading as a project reference
- accepts profile skills represented either as strings or dicts with `name`
- logs full validation failure details in pipeline runs

### Versioning and Tracking

Implemented in [`tracker.py`](/workspaces/fitcv/src/fitcv/tracker.py).

Current stored artifacts:

- `cv_versions`
- `application_tracker`

`create_cv_version_record()` stores:

- `job_url`
- enrichment and prompt versions
- vector rank
- AI score
- final score
- evidence IDs
- CV markdown
- gap summary
- fit classification

## BigQuery Assets

The current table DDL set lives under [`assets/bigquery`](/workspaces/fitcv/assets/bigquery).

Implemented assets include:

- `raw_jobs.sql`
- `structured_jobs.sql`
- `candidate_profile.sql`
- `candidate_experiences.sql`
- `candidate_projects.sql`
- `candidate_skills.sql`
- `candidate_achievements.sql`
- `candidate_certifications.sql`
- `candidate_education.sql`
- `job_embeddings.sql`
- `candidate_embeddings.sql`
- `rule_filter_results.sql`
- `vector_shortlist.sql`
- `ai_score_results.sql`
- `final_ranking.sql`
- `evidence_retrieval.sql`
- `gap_analysis.sql`
- `cv_versions.sql`
- `application_tracker.sql`

## Verified Runtime Status

Current verified non-integration test status on `main`:

- `274 passed, 7 skipped`

Current verified pipeline smoke result against [`data/sample_jobs.json`](/workspaces/fitcv/data/sample_jobs.json):

```python
{
    "total_jobs": 7,
    "passed_filter": 1,
    "ranked": 1,
    "cvs_generated": 1,
}
```

This confirms the current end-to-end happy path:

- one job survives rule filtering
- ranking remains consistent with the filtered universe
- at least one validated CV can be generated and stored

## Known Limitations and Follow-Ups

- some Vertex SDK deprecation warnings still appear in live runs, indicating remaining code paths that still touch deprecated Vertex helpers
- the implementation is still optimized for local JSON ingestion; remote source ingestion is not the active primary path
- live runs remain quota-sensitive and depend on Gemini/Vertex availability
- backward compatibility for both `.env.yaml` and `config/env.yaml` is still present; canonical-file cleanup is not yet done
- strict `mypy` configuration exists, but the repository still has unresolved typing debt and missing third-party stubs

## File Map

Primary runtime files:

- [`src/fitcv/config.py`](/workspaces/fitcv/src/fitcv/config.py)
- [`src/fitcv/pipeline.py`](/workspaces/fitcv/src/fitcv/pipeline.py)
- [`src/fitcv/ingest.py`](/workspaces/fitcv/src/fitcv/ingest.py)
- [`src/fitcv/normalize.py`](/workspaces/fitcv/src/fitcv/normalize.py)
- [`src/fitcv/enrich.py`](/workspaces/fitcv/src/fitcv/enrich.py)
- [`src/fitcv/candidate.py`](/workspaces/fitcv/src/fitcv/candidate.py)
- [`src/fitcv/embeddings.py`](/workspaces/fitcv/src/fitcv/embeddings.py)
- [`src/fitcv/rule_filter.py`](/workspaces/fitcv/src/fitcv/rule_filter.py)
- [`src/fitcv/vector_search.py`](/workspaces/fitcv/src/fitcv/vector_search.py)
- [`src/fitcv/ai_score.py`](/workspaces/fitcv/src/fitcv/ai_score.py)
- [`src/fitcv/ranking.py`](/workspaces/fitcv/src/fitcv/ranking.py)
- [`src/fitcv/evidence.py`](/workspaces/fitcv/src/fitcv/evidence.py)
- [`src/fitcv/gap_analysis.py`](/workspaces/fitcv/src/fitcv/gap_analysis.py)
- [`src/fitcv/cv_generator.py`](/workspaces/fitcv/src/fitcv/cv_generator.py)
- [`src/fitcv/validator.py`](/workspaces/fitcv/src/fitcv/validator.py)
- [`src/fitcv/tracker.py`](/workspaces/fitcv/src/fitcv/tracker.py)

## Change Policy for This Document

This file should be updated when any of the following change on `main`:

- pipeline stage ordering
- config keys or loader behavior
- model defaults or auth paths
- validation rules
- BigQuery table contracts
- verified end-to-end pipeline behavior
