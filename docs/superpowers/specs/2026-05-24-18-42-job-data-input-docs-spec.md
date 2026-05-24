---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: Job-data input docs SSOT (LinkedIn via Apify)
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-input-mode-parity
targets:
  - README.md
  - docs/job-data-input.md
  - docs/pipeline.md
related_features: []
related_stages: []
---

# Spec: Job-data input docs SSOT (LinkedIn via Apify)

## Problem

Current docs describe pipeline stages but do not clearly define:

- upstream job data source and scraping setup (Apify actor)
- accepted job input formats and required fields
- normalization and dedupe rules applied before downstream stages
- limitations and reproducibility expectations for scraped job datasets

This creates operator/engineer ambiguity and makes repeated runs harder to reproduce.

## Goal

- One “single source of truth” doc for job-data input contract and transforms.
- Minimal README and pipeline doc pointers to make the SSOT discoverable.
- Keep scope doc-only (no runtime behavior changes).

## Non-Goals

- Changing ingestion logic, schema, or storage behavior.
- Building a first-class Apify-dataset input mode into the control plane.
- Expanding into a full data governance/compliance policy doc.

## Key Deliverables

- `docs/job-data-input.md` exists and is SSOT for:
  - upstream source + scraping setup
  - accepted input shapes + required fields
  - normalization + dedupe semantics
  - limitations + reproducibility checklist
- `README.md` links to `docs/job-data-input.md`.
- `docs/pipeline.md` points to `docs/job-data-input.md` from pipeline overview.

## Proposed doc structure

Create `docs/job-data-input.md` with:

- data source: LinkedIn scraped via Apify actor `bebity/linkedin-jobs-scraper`
- scraping setup and reproducibility checklist (actor input + dataset snapshot)
- input formats:
  - file input via `jobs_path` (top-level JSON array)
  - engineering helper note: `fetch_from_apify(config)` in `src/fitcv/ingest.py`
- required fields and common optional fields (scraper shape)
- camelCase → snake_case mapping notes
- normalize-stage transforms:
  - whitespace normalization
  - best-effort parsing for applicant count and salary
  - dedupe semantics (exact + near-duplicate)
- limitations (localization, job churn, parsing best-effort)

Update discoverability:

- add small README section linking to SSOT
- add pointer in `docs/pipeline.md` to SSOT

## Task/Wave Breakdown

### Task 1: Draft SSOT doc

- Describe upstream source: LinkedIn via Apify actor `bebity/linkedin-jobs-scraper`.
- Define accepted inputs:
  - file input via `jobs_path` (top-level JSON array)
  - engineering helper: `fetch_from_apify(config)` in `src/fitcv/ingest.py`
- List required fields and common optional fields from scraper output.
- Document normalization + dedupe behavior (align to `src/fitcv/normalize.py`).
- Document limitations and reproducibility checklist.

### Task 2: Add doc pointers

- Add minimal README section linking to SSOT.
- Add pipeline overview pointer in `docs/pipeline.md` to SSOT.

## Design Decisions

- SSOT lives in `docs/job-data-input.md` to keep `README.md` concise.
- Treat Apify dataset fetch as engineering helper; recommend file snapshot for reproducibility.
- Describe required fields as scraper contract aligned to `REQUIRED_SCRAPER_FIELDS`.

## Invariants

- Doc-only lane: no runtime behavior changes.
- Doc claims must match code behavior in `src/fitcv/ingest.py` and `src/fitcv/normalize.py`.
- Public docs must not depend on private-only operating-system materials.

## Validation Plan

- Run `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`.
- If spec/plan artifacts change, regenerate planning lineage:
  `.\.venv\Scripts\python.exe scripts/generate_planning_lineage.py`.

## Completion Criteria

- Key Deliverables met.
- `scripts/validate_repo_contracts.py --fast` passes.

## Acceptance criteria

- `docs/job-data-input.md` present and referenced by `README.md` and `docs/pipeline.md`.
- Doc claims align with actual code behavior in:
  - `src/fitcv/ingest.py`
  - `src/fitcv/normalize.py`
- Repo contract checks pass (`scripts/validate_repo_contracts.py --fast`).
