---
layer: change
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: completed
name: fitcv-indeed-input-contract
targets:
  - src/fitcv/contracts.py
  - src/fitcv/ingest.py
  - tests/test_ingest.py
  - tests/test_fitcv_cp/test_app.py
  - docs/job-data-input.md
---

# FitCV Indeed Input Contract

## Goal

Allow the Run upload preflight to accept the Indeed scraper JSON shape already
supported by the normalize stage, without weakening validation for existing
canonical/LinkedIn-shaped job input.

The uploaded Indeed records must pass the same control-plane canonicalization
and persistence path as other job input. Existing raw field names and source
order must remain unchanged in the canonical artifact; provider-specific
mapping remains owned by `src/fitcv/ingest.py` during normalization.

## Implementation Outcomes

### Provider-aware ingress validation

`canonicalize_jobs()` selects validation based on the existing Indeed shape
detection. Indeed records with `url`, `title`, and `description` are accepted
without requiring LinkedIn-only fields such as `companyName`, `contractType`,
or `experienceLevel`. Existing LinkedIn/canonical input keeps its current
required-field validation and error behavior.

### Run upload compatibility

The multipart Run upload route accepts the supplied Indeed JSON file, creates
the normal immutable job-input artifact, and reaches pipeline submission
without a preflight `422 validation_failed` response. Malformed Indeed rows
still fail with indexed, field-specific validation errors. The immutable raw
artifact remains unchanged while the persisted `run_jobs` projection receives
the snake-case Indeed normalization required by SQLite scalar columns.

### Contract documentation and regression proof

The job-input contract distinguishes accepted raw ingress shapes from the
snake-case normalized pipeline shape. Unit and direct API tests cover Indeed
success, Indeed failure, existing contract rejection, artifact preservation,
and Run upload side effects.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-writing-plans`, `skill-backend-verification`, `skill-test-driven-development`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: inspect and edit declared plan-owned source, tests, and documentation; run declared local checks; preserve unrelated dirty files
- User-approval actions: push, merge, publication, destructive cleanup, discard, or changes outside declared ownership
- Parallel ownership: none
- Sequential fallback: complete contract change, then tests, then documentation and final verification

## Task Breakdown

### Task 1: Add provider-aware canonical input validation

**Purpose:**
- Make the control-plane validator accept the existing Indeed scraper shape while preserving current validation for other sources.

**Task Function:**
- Extend the canonical ingress contract without changing downstream normalization or raw artifact serialization.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: small, design-clear backend contract change with existing helpers and tests.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused unit and route tests provide bounded proof.

**Specification Coverage:**
- Provider-aware ingress validation.
- Existing LinkedIn/canonical validation remains unchanged.
- Canonical artifact preserves raw Indeed records and deterministic digest behavior.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/contracts.py:REQUIRED_SCRAPER_FIELDS`, `src/fitcv/ingest.py:canonicalize_jobs`, `src/fitcv/ingest.py:validate_linkedin_schema`, `src/fitcv/ingest.py:_is_indeed_job`
- Modify: `src/fitcv/contracts.py` for the Indeed minimum-field contract; `src/fitcv/ingest.py` for provider-aware validation selection
- Verify: `tests/test_ingest.py`

**Dependencies:**
- Existing `_is_indeed_job()` and `_normalize_indeed_job()` remain the source of truth for recognizing and processing current Indeed records.
- Do not modify `snake_case_keys()`, `prepare_raw_rows()`, or pipeline stage ordering in this task.

**Authority:**
- Preauthorized local actions: edit `src/fitcv/contracts.py` and `src/fitcv/ingest.py`, add focused unit tests, and run declared local checks.
- Stop for: discovered need to change pipeline stage behavior, persisted schemas, or unrelated dirty files.

**Steps:**
- [x] Step 1: Add an explicit Indeed minimum-field tuple in `src/fitcv/contracts.py`; require `url`, `title`, and `description`, while leaving nested employer, location, and job-type fields optional because current Indeed normalization has fallbacks.
- [x] Step 2: Add a provider-aware validation selector in `src/fitcv/ingest.py`; route Indeed-shaped rows to Indeed validation and all other rows to existing `validate_linkedin_schema()` behavior.
- [x] Step 3: Update `canonicalize_jobs()` to call the selector while preserving object order, raw keys, UTF-8 serialization, and SHA-256 output.

**Verification:**
- [x] `pytest -q tests/test_ingest.py -k "canonicalize_jobs or validate or indeed"` — passed.
- Expected: Indeed-shaped rows pass; missing Indeed required fields fail with row index and field name; existing canonical rows retain current behavior; serialization tests remain green.

**Exit Criteria:**
- `canonicalize_jobs()` accepts the supplied Indeed record shape and rejects malformed rows without weakening the existing canonical contract.

### Task 2: Prove Run upload boundary behavior

**Purpose:**
- Verify the actual control-plane endpoint that produced the browser error, not only the lower-level parser.

**Task Function:**
- Add direct success and failure regression coverage for multipart Run upload validation and persistence.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing app test harness already seeds profiles and patches queue submission.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: route assertions cover boundary status, persisted input, and failure response.

**Specification Coverage:**
- Run upload compatibility.
- Malformed Indeed validation remains indexed and field-specific.
- Immutable upload artifact reaches normal Run creation side effects.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:10027-10034`, `tests/test_fitcv_cp/test_app.py:test_real_run_route_accepts_upload_only_and_scan_only`, existing `_app()`, `_seed_active_profile()`, and `_valid_fitcv_job()` helpers
- Modify: `tests/test_fitcv_cp/test_app.py`
- Verify: `src/fitcv_cp/app.py:POST /runs` through `TestClient`

**Dependencies:**
- Task 1 provider-aware validator is complete.
- Preserve current test isolation and patch `submit_run`; do not invoke external LLM, queue, or browser services.

**Authority:**
- Preauthorized local actions: add route tests in `tests/test_fitcv_cp/test_app.py` and run focused control-plane checks.
- Stop for: route behavior requiring frontend changes, database migrations, or external service authentication.

**Steps:**
- [x] Step 1: Add a compact Indeed fixture containing the raw keys from the supplied file, including nested `employer`, `location`, `jobTypes`, and object-form `description`.
- [x] Step 2: POST that fixture to `/runs` as `jobs_file` with an active profile and patched submission; assert `201`, upload source metadata, persisted job-input JSON retaining raw Indeed keys, and a scalar `run_jobs.location` projection.
- [x] Step 3: POST a malformed Indeed fixture missing `url`, `title`, or `description`; assert `422` and the indexed validation message.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_app.py -q -k "indeed"` — `4 passed`.
- Expected: valid Indeed upload creates a Run; malformed Indeed upload is rejected before submission; no existing upload/scan tests regress.

**Exit Criteria:**
- The exact UI-triggered route accepts the supplied schema and persists it through the existing Run input path.

### Task 3: Align job-input documentation

**Purpose:**
- Remove the documented LinkedIn-only assumption that caused the contract mismatch.

**Task Function:**
- Document raw ingress contracts separately from normalized pipeline fields.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: one canonical data-contract document needs a focused wording update.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: source and test proof establish the contract.

**Specification Coverage:**
- Contract documentation and regression proof.
- Single source of truth remains `src/fitcv/contracts.py` and `src/fitcv/ingest.py`.

**Required Skills:**
- `none`

**Files And Symbols:**
- Inspect: `docs/job-data-input.md:Canonical artifact`, `docs/job-data-input.md:Downstream behavior`
- Modify: `docs/job-data-input.md`
- Verify: wording matches `src/fitcv/contracts.py` and `src/fitcv/ingest.py`

**Dependencies:**
- Tasks 1 and 2 establish the accepted Indeed fields and route behavior.

**Authority:**
- Preauthorized local actions: update `docs/job-data-input.md` to reflect implemented provider-aware validation.
- Stop for: documentation requiring a new product contract beyond Indeed upload acceptance.

**Steps:**
- [x] Step 1: Replace the statement that every raw job requires `companyName`, `contractType`, and `experienceLevel` with an ingress-shape section covering canonical/LinkedIn and Indeed records.
- [x] Step 2: State that normalization maps Indeed `employer`, `jobTypes`, and `description` into the existing snake-case pipeline shape after Run artifact creation.
- [x] Step 3: Keep source order, raw serialization, digest, and downstream normalization ownership explicit.

**Verification:**
- [x] `rg -n "companyName|contractType|experienceLevel|Indeed|normalized" docs/job-data-input.md` — contract text aligned.
- Expected: documentation describes both accepted ingress shapes and does not claim Indeed must contain LinkedIn-only fields.

**Exit Criteria:**
- Documentation matches the provider-aware validator and current Indeed normalization path.

## Verification

- [x] `pytest -q tests/test_ingest.py tests/test_fitcv_cp/test_app.py` — `528 passed, 1 skipped`.
- [x] `git diff --check` — passed; Git reported existing LF/CRLF warnings only.
- [x] Local smoke check against `data/dataset_indeed-jobs-scraper_2026-09-16_20-16-35-737.json` — `100` records canonicalized.
- Expected: focused ingest and control-plane suites pass, no whitespace errors exist, and the supplied dataset reaches canonicalization before any external pipeline service is required.

Residual test-run warning: Windows temporary SQLite cleanup emitted `PermissionError [WinError 32]` after successful test exit; no test failed and no plan-owned file was affected.

## Completion Criteria

The plan is ready for completion verification when:

1. `canonicalize_jobs()` accepts the supplied Indeed schema and preserves existing canonical/LinkedIn validation.
2. Direct `POST /runs` upload proof shows valid Indeed input creates a Run and malformed input returns indexed `422` validation.
3. `docs/job-data-input.md` matches the implemented ingress and normalization contracts.
4. Declared tests and checks pass with unrelated dirty files preserved.
5. No salary, benefits, ranking, frontend, or provider-acquisition changes are included in this patch.
