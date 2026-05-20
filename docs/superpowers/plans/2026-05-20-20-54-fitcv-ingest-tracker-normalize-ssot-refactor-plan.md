---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-ingest-tracker-normalize-ssot-refactor-plan
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract
parent_spec: docs/superpowers/specs/2026-05-03-pipeline-efficiency-exact-match-contract-bootstrap-spec.md
targets:
  - src/fitcv/ingest.py
  - src/fitcv/tracker.py
  - src/fitcv/normalize.py
  - src/fitcv/persistence.py
  - tests/test_ingest.py
  - tests/test_tracker.py
  - tests/test_normalize.py
related_features:
  - cv_system
---

## Goal

Execute RF-001..RF-005 as bounded refactor/optimization pass for ingest, tracker, normalize surfaces to enforce SSOT, structural symmetry, and invariance while preserving externally expected pipeline behavior.

## Key Deliverables

### Deliverable 1: Backend persistence symmetry

`ingest` and `tracker` use one shared BigQuery/sqlite policy path (credential fallback, sqlite path resolution, and client construction) with no module-local divergence.

### Deliverable 2: Shared contract surfaces

Field mapping, required scraper fields, and status/default contracts move to one canonical runtime contract surface consumed by both ingest and normalize/tracker flows.

### Deliverable 3: Normalization and dedupe invariance

Deduplication and parser behavior are refactored to remove hidden duplication, enforce explicit edge-case outcomes, and keep stable downstream artifact semantics.

### Deliverable 4: Compatibility-safe tracking writes

CV version write fallback (structured->legacy schema) remains backward compatible with clearer, deterministic error matching and explicit coverage tests.

## Task/Wave Breakdown

### Task 1: Baseline and guardrails capture

**Purpose:**
- Lock current behavior and dependency blast radius before refactor edits.

**Files:**
- Inspect: `src/fitcv/ingest.py`
- Inspect: `src/fitcv/tracker.py`
- Inspect: `src/fitcv/normalize.py`
- Verify: `tests/test_ingest.py`
- Verify: `tests/test_tracker.py`
- Verify: `tests/test_normalize.py`

**Preconditions:**
- GitNexus freshness is `fresh` for current HEAD.
- GitNexus impact/context captured for target symbols (`snake_case_keys`, `load_to_bigquery`, `normalize_batch_with_exclusions`, `parse_salary`, `parse_applications_count`, `store_cv_version`, `store_application_status`).

**Steps:**
- [ ] Step 1: Run targeted `gitnexus impact` for each edited symbol and record risk in execution notes.
- [ ] Step 2: Snapshot current tests for scoped modules to detect behavior drift quickly.
- [ ] Step 3: Confirm no unrelated code rollback in dirty worktree.

**Verification:**
- [ ] `npx gitnexus impact <symbol> -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`
- [ ] `uvx pytest tests/test_ingest.py tests/test_tracker.py tests/test_normalize.py`

**Exit Criteria:**
- Symbol-level risk map exists and baseline tests are green or known-failing with recorded reason.

### Task 2: RF-001 persistence SSOT alignment

**Purpose:**
- Remove credential/sqlite policy drift between ingest and tracker.

**Files:**
- Inspect: `src/fitcv/persistence.py`
- Modify: `src/fitcv/ingest.py`
- Modify: `src/fitcv/tracker.py`
- Verify: `tests/test_ingest.py`
- Verify: `tests/test_tracker.py`

**Preconditions:**
- Task 1 complete.

**Steps:**
- [ ] Step 1: Route BigQuery client creation in ingest/tracker through shared persistence helper.
- [ ] Step 2: Route sqlite path resolution through shared helper instead of module-local duplicate functions.
- [ ] Step 3: Normalize credential fallback behavior (ADC when key missing) across both tracker write paths and ingest write path.

**Verification:**
- [ ] `uvx pytest tests/test_ingest.py -k bigquery_mode`
- [ ] `uvx pytest tests/test_tracker.py -k store_cv_version`

**Exit Criteria:**
- No module-local credential policy divergence remains in scoped files.

### Task 3: RF-002 contract SSOT extraction

**Purpose:**
- Create one canonical contract source for equivalent field/status concepts.

**Files:**
- Modify: `src/fitcv/contracts.py` (new or extended)
- Modify: `src/fitcv/ingest.py`
- Modify: `src/fitcv/tracker.py`
- Modify: `tests/test_ingest.py`
- Modify: `tests/test_tracker.py`

**Preconditions:**
- Task 2 complete.

**Steps:**
- [ ] Step 1: Extract scraper key map + required scraper field list + default application statuses to shared contract module.
- [ ] Step 2: Replace module-local duplicates with imports from shared contract module.
- [ ] Step 3: Add contract-focused tests asserting mapping/status invariants remain stable.

**Verification:**
- [ ] `uvx pytest tests/test_ingest.py -k "snake_case_keys or validate_linkedin_schema"`
- [ ] `uvx pytest tests/test_tracker.py -k update_application_status`

**Exit Criteria:**
- Equivalent concepts no longer defined in multiple scoped modules.

### Task 4: RF-003 normalization symmetry and dedupe refactor

**Purpose:**
- Eliminate hidden duplication in dedupe logic while preserving pipeline-visible outcomes.

**Files:**
- Modify: `src/fitcv/normalize.py`
- Verify: `src/fitcv/pipeline.py`
- Modify: `tests/test_normalize.py`
- Verify: `tests/test_pipeline.py`

**Preconditions:**
- Task 3 complete.

**Steps:**
- [ ] Step 1: Consolidate exact and near-dedupe keying into shared internal helper path used by both standalone and exclusion-aware batch flow.
- [ ] Step 2: Keep dedupe reason labels and ordering invariants unchanged (`duplicate_job_url`, `near_duplicate_job_posting`, input-order sorting).
- [ ] Step 3: Add symmetry tests proving helper-backed and batch-backed dedupe behavior stays equivalent.

**Verification:**
- [ ] `uvx pytest tests/test_normalize.py`
- [ ] `uvx pytest tests/test_pipeline.py -k dedupe`

**Exit Criteria:**
- One dedupe algorithmic surface owns key construction + exclusion tagging behavior.

### Task 5: RF-004 parser edge-case hardening

**Purpose:**
- Resolve parser contradictions/edge drift with explicit invariants.

**Files:**
- Modify: `src/fitcv/normalize.py`
- Modify: `tests/test_normalize.py`
- Verify: `tests/test_rule_filter.py`

**Preconditions:**
- Task 4 complete.

**Steps:**
- [ ] Step 1: Define explicit policy for mixed salary unit/currency strings (reject or normalize deterministically).
- [ ] Step 2: Expand applicant-count parser contract for accepted localized/variant phrases or explicit `None` fallback semantics.
- [ ] Step 3: Add regression tests for mixed currency/period and non-English/variant applicant strings.

**Verification:**
- [ ] `uvx pytest tests/test_normalize.py -k "salary or applications_count"`
- [ ] `uvx pytest tests/test_rule_filter.py -k applications_count`

**Exit Criteria:**
- Parser behavior for known risky edge cases is explicit, test-locked, and documented in code comments where necessary.

### Task 6: RF-005 resilient legacy fallback contract

**Purpose:**
- Make structured-column-missing fallback robust without over-matching unrelated BigQuery errors.

**Files:**
- Modify: `src/fitcv/tracker.py`
- Modify: `tests/test_tracker.py`

**Preconditions:**
- Task 2 complete.

**Steps:**
- [ ] Step 1: Refine missing-column detection to prefer structured fields/reasons/locations over brittle message fragments.
- [ ] Step 2: Preserve current backward-compatibility retry path (`structured` write then `legacy` write) only for qualifying schema-missing errors.
- [ ] Step 3: Add tests for both qualifying and non-qualifying error payloads.

**Verification:**
- [ ] `uvx pytest tests/test_tracker.py -k "legacy_schema or structured_columns"`

**Exit Criteria:**
- Fallback triggers only for intended schema-migration gaps.

### Task 7: Cross-surface verification and closure

**Purpose:**
- Prove invariants preserved and change scope controlled.

**Files:**
- Verify: `src/fitcv/ingest.py`
- Verify: `src/fitcv/tracker.py`
- Verify: `src/fitcv/normalize.py`
- Verify: `tests/test_ingest.py`
- Verify: `tests/test_tracker.py`
- Verify: `tests/test_normalize.py`

**Preconditions:**
- Tasks 2-6 complete.

**Steps:**
- [ ] Step 1: Run full scoped test suite and type check for edited modules.
- [ ] Step 2: Run `gitnexus_detect_changes` to verify expected symbol/process blast radius.
- [ ] Step 3: Record migration/deprecation notes (if any behavior changed under RF-004).

**Verification:**
- [ ] `uvx pytest tests/test_ingest.py tests/test_tracker.py tests/test_normalize.py`
- [ ] `uvx mypy src --show-error-codes`
- [ ] `npx gitnexus detect_changes -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`

**Exit Criteria:**
- All scoped tests pass, type check clean (or known/approved exceptions), and GitNexus change map matches expected scope.

## Verification

- `uvx pytest tests/test_ingest.py tests/test_tracker.py tests/test_normalize.py`
- `uvx pytest tests/test_pipeline.py -k dedupe`
- `uvx pytest tests/test_rule_filter.py -k applications_count`
- `uvx mypy src --show-error-codes`
- `npx gitnexus detect_changes -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`
- `python scripts/hooks/run_validator.py --fast`

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
