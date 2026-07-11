---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: indeed-job-input-adapter
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-input-mode-parity
parent_spec: docs/superpowers/specs/2026-06-26-00-49-indeed-job-input-adapter-spec.md
targets:
  - src/fitcv/ingest.py
  - src/fitcv/contracts.py
  - tests/test_ingest.py
  - tests/test_normalize.py
related_features: []
related_stages: []
---

# Indeed Job Input Adapter Plan

## Goal

Implement the Indeed ingest adapter from the approved spec with the smallest possible change set. Indeed records should flow into the existing canonical job pipeline without touching normalize, enrich, ranking, or generation logic. Execution should prove this against the light dataset `data/dataset_indeed-jobs-scraper_2026-06-25_23-11-47-317.json`.

## Key Deliverables

### Indeed records map into current canonical job rows

Add a thin source adapter at ingest time so Indeed payloads produce the same canonical keys the LinkedIn path already uses.

### Regression coverage proves both sources still work

Add focused tests that prove Indeed input is accepted and LinkedIn behavior stays unchanged.

## Task/Wave Breakdown

### Task 1: Add Indeed source adapter at ingest boundary

**Purpose:**
- translate Indeed raw records into canonical job dicts before shared normalization runs

**Files:**
- Inspect: `src/fitcv/ingest.py`
- Inspect: `src/fitcv/contracts.py`
- Modify: `src/fitcv/ingest.py`
- Modify: `src/fitcv/contracts.py`

**Preconditions:**
- approved spec exists
- current LinkedIn ingest path remains source of truth for canonical output shape

**Steps:**
- [x] Step 1: add source detection for Indeed records using stable top-level markers such as `url`, `dateOnIndeed`, and nested `employer` / `jobTypes`, without requiring `description` to stay nested
- [x] Step 2: map Indeed fields into existing canonical keys, including `url -> job_url`, `employer.name -> company_name`, `employer.companyPageUrl -> company_url`, `description.text -> description`, and `datePublished -> published_at`
- [x] Step 3: keep location text readable by avoiding raw `admin1Code` noise when a cleaner city/country string is enough
- [x] Step 4: keep `attributes` raw-only and preserve original JSON in `raw_json`
- [x] Step 5: keep fallback behavior for LinkedIn records unchanged

**Verification:**
- [x] inspect resulting canonical row shape against existing `prepare_raw_rows` contract

**Exit Criteria:**
- Indeed and LinkedIn both land in same canonical row shape

### Task 2: Add regression tests for Indeed and LinkedIn parity

**Purpose:**
- prove adapter behavior and protect current LinkedIn flow from drift

**Files:**
- Inspect: `tests/test_ingest.py`
- Inspect: `tests/test_normalize.py`
- Modify: `tests/test_ingest.py`
- Modify: `tests/test_normalize.py`

**Preconditions:**
- Task 1 mapping is defined

**Steps:**
- [x] Step 1: add unit test covering plain-string Indeed `description` so adapter keeps using `url -> job_url`
- [x] Step 2: add unit test covering cleaner location rendering from live Indeed shape
- [x] Step 3: keep test proving `attributes` stays raw-only and does not affect canonical output
- [x] Step 4: add test proving normalized Indeed rows dedupe through shared `job_url` path
- [x] Step 5: keep existing LinkedIn tests unchanged so regression coverage stays intact

**Verification:**
- [x] `pytest tests/test_ingest.py tests/test_normalize.py`

**Exit Criteria:**
- tests prove adapter works and current LinkedIn contract still passes

## Verification

- `pytest tests/test_ingest.py tests/test_normalize.py`
- live smoke on `data/dataset_indeed-jobs-scraper_2026-06-25_23-11-47-317.json`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
