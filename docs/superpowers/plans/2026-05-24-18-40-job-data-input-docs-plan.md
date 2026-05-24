---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: Document job-data input pipeline (LinkedIn via Apify)
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-input-mode-parity
parent_spec: docs/superpowers/specs/2026-05-24-18-42-job-data-input-docs-spec.md
targets:
  - README.md
  - docs/job-data-input.md
  - docs/pipeline.md
related_features: []
related_stages: []
---

# Implementation Plan: Document job-data input pipeline (LinkedIn via Apify)

## Goal

Make job-data ingestion docs explicit and reproducible:

- name upstream data source (LinkedIn via Apify actor `bebity/linkedin-jobs-scraper`)
- define accepted input shapes and required fields
- document normalization + dedupe transformations
- explain how downstream pipeline stages consume this data
- capture limitations + reproducibility checklist

## Key Deliverables

- `docs/job-data-input.md` exists as single source of truth for job-data input.
- `README.md` links to job-data SSOT and explains expected `jobs_path` shape.
- `docs/pipeline.md` points to job-data SSOT from pipeline overview.

## Task/Wave Breakdown

### Task 1: Create SSOT doc

- [x] Add `docs/job-data-input.md` with:
  - data source and Apify actor reference
  - file input format (`jobs_path`) and schema expectations
  - engineering helper note for Apify dataset fetch (`fetch_from_apify`)
  - key fields (required + common optional)
  - cleaning/transforms (snake_case mapping, whitespace, parsing)
  - dedupe semantics
  - limitations + reproducibility checklist

### Task 2: Update navigation pointers

- [x] Update `README.md` to include “Job Data Input (LinkedIn via Apify)” section linking to SSOT.
- [x] Update `docs/pipeline.md` to point to `docs/job-data-input.md` from pipeline overview.

### Task 3: Verification (closure-evidence)

- [x] GitNexus scope check: `npx gitnexus detect_changes --scope staged --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"` (PASS: reported `No changes detected.`).
- [x] Repo contracts: `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast` (PASS).
- [x] Planning lifecycle: `.\.venv\Scripts\python.exe scripts/validate_planning_lifecycle.py --strict` (PASS).
- [x] Checkpoint packs: `.\.venv\Scripts\python.exe scripts/validate_checkpoint_packs.py` (PASS).

## Completion Criteria

- [x] Deliverables satisfied.
- [x] No unresolved checklist items remain in this plan.

## Verification

- [x] `npx gitnexus detect_changes --scope staged --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"` (PASS: `No changes detected.`)
- [x] `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast` (PASS)
- [x] `.\.venv\Scripts\python.exe scripts/validate_planning_lifecycle.py --strict` (PASS)
- [x] `.\.venv\Scripts\python.exe scripts/validate_checkpoint_packs.py` (PASS)
