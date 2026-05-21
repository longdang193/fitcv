---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: synonym-triage-cross-run-reuse-fingerprint-remediation
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
parent_spec: docs/superpowers/specs/2026-04-28-operator-control-plane-agentic-settings-surface-spec.md
targets:
  - src/fitcv_cp/synonym_proposals.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
related_stages:
  - enrich
  - cv_analysis
---

## Goal

Enable true cross-run synonym triage recommendation reuse by removing run-scoped identity drift from triage fingerprints, while preserving run-local proposal workflow and UI behavior.

## Key Deliverables

### Stable cross-run triage identity contract

Synonym proposal triage reuse key no longer depends on run-scoped identifiers (`run_id`/run-seeded `proposal_id`). Identical semantic proposal content with unchanged triage runtime inputs can reuse prior recommendation metadata across runs.

### Symmetric triage behavior across execution paths

Both execution-time automation path and admin triage-refresh path use same stable triage fingerprint contract and same reuse reason semantics.

### Regression coverage for reuse drift

Tests lock expected behavior for:
- cross-run reuse hit when proposal semantics unchanged
- forced recompute on meaningful input/runtime changes
- preservation of proposal status/history semantics

## Task/Wave Breakdown

### Task 1: Baseline and contract definition for reuse identity

**Purpose:**
- Define canonical stable fingerprint payload fields and drift boundaries before edits.

**Files:**
- Inspect: `src/fitcv_cp/synonym_proposals.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/app.py`
- Verify: `artifacts/live_run_e9246134/unzipped/synonym-proposals-trace.json`

**Preconditions:**
- GitNexus index refreshed (`npx gitnexus analyze`) for cross-file dependency tracing.

**Steps:**
- [x] Step 1: Document current mismatch (`enrich` cross-run reuse vs triage run-scoped reuse) with source references.
- [x] Step 2: Define stable triage key contract: `field`, `alias`, `canonical`, sorted `candidate_canonicals`, proposal family, provider/model/wire_api, triage-version, overlay fingerprint.
- [x] Step 3: Explicitly exclude run-scoped identity (`run_id`, run-seeded `proposal_id`) from reuse key.

**Verification:**
- [x] Source inspection confirms all current fingerprint callsites and payload builders mapped.

**Exit Criteria:**
- Stable-key contract accepted and mapped to all affected callsites.

### Task 2: Decouple proposal persistence identity from triage reuse identity

**Purpose:**
- Preserve run-local proposal row identity while introducing reusable semantic identity.

**Files:**
- Modify: `src/fitcv_cp/synonym_proposals.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 stable-key contract complete.

**Steps:**
- [x] Step 1: Introduce explicit semantic-stable identity field for proposals (or equivalent helper output) independent of run-seeded `proposal_id`.
- [x] Step 2: Keep `proposal_id` behavior compatible for UI actions/forms/history references.
- [x] Step 3: Ensure payload merge logic can reuse existing recommendation runtime metadata via stable identity path.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_app.py -k "synonym_triage_fingerprint_is_stable_across_run_scoped_proposal_ids or reuses_existing_state_by_identity_across_runs"`

**Exit Criteria:**
- Proposal payload supports stable reuse identity without breaking run-local review actions.

### Task 3: Unify stable fingerprint usage in automation and admin triage paths

**Purpose:**
- Remove split-brain behavior where one path can drift from another.

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete.

**Steps:**
- [x] Step 1: Refactor worker automation triage fingerprint payload to stable semantic key.
- [x] Step 2: Refactor admin triage-refresh fingerprint helper to same stable semantic key contract.
- [x] Step 3: Align reuse reason labels and counters (`reused_count`, `fresh_count`, trace summary fields) across both paths.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py -k "synonym_proposals"`
- [x] `python -m pytest -q tests/test_fitcv_cp/test_app.py -k "triage_refresh_reuses_when_fingerprint_matches_across_run_ids"`

**Exit Criteria:**
- Equivalent inputs produce equivalent reuse outcomes regardless of path.

### Task 4: Add regression tests for cross-run reuse and recompute boundaries

**Purpose:**
- Prevent future regressions back to run-scoped reuse drift.

**Files:**
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 3 complete.

**Steps:**
- [x] Step 1: Add test: same semantic proposals across two runs yields non-zero reused triage count on second run.
- [x] Step 2: Add test: changing canonical/candidate set/runtime fingerprint forces recompute (`fresh_count` increments).
- [x] Step 3: Add test: run-local proposal action routes (`proposal_id` forms/endpoints) remain functional.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_app.py -k "triage_refresh_reuses_when_fingerprint_matches_across_run_ids or triage_refresh_recomputes_when_runtime_fingerprint_changes"`
- [x] `python -m pytest -q tests/test_fitcv_cp/test_app.py -k "approve_synonym_proposal or admin_run_synonym_proposal_action_redirects_to_run_detail or admin_run_synonym_proposal_action_blocked_when_apply_to_run_disabled"`

**Exit Criteria:**
- Test suite enforces both reuse correctness and UI/action compatibility.

### Task 5: Live-run evidence validation and drift closeout

**Purpose:**
- Prove fix in runtime artifacts, not only unit tests.

**Files:**
- Verify: `artifacts/live_run_*/unzipped/enrich.json`
- Verify: `artifacts/live_run_*/unzipped/synonym-proposals-trace.json`
- Verify: `artifacts/live_run_*/unzipped/settings-used.json`

**Preconditions:**
- Tasks 1-4 complete and containers rebuilt with patched code.

**Steps:**
- [x] Step 1: Trigger live run with unchanged input pair used in previous baseline.
- [x] Step 2: Confirm enrich reuse still behaves independently (`reused_rows` may stay high).
- [x] Step 3: Confirm triage trace now shows expected reuse hits when inputs stable.
- [x] Step 4: Capture mismatch guard: if proposal semantics changed materially, triage fresh/recompute remains expected.

**Verification:**
- [x] `docker compose up -d --build web worker`
- [x] `Invoke-RestMethod` trigger + artifact download checks
- [x] Compare `triage_recommendation_reused_total` second run vs first run (note: cache already warm; both runs showed non-zero reuse)

**Exit Criteria:**
- Artifact evidence demonstrates intended cross-run triage reuse with correct invalidation boundaries.

## Verification

- `npx gitnexus analyze`
- `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py -k "triage_recommendation or cross_run or triage_reuse"`
- `python -m pytest -q tests/test_fitcv_cp/test_app.py -k "synonym triage refresh or proposal_id or synonym_proposal"`
- Live-run artifact comparison for `enrich.json` and `synonym-proposals-trace.json` across two consecutive runs

## Completion Criteria

1. Triage reuse key is semantically stable across runs and excludes run-scoped identity fields.
2. Worker and admin triage paths share same fingerprint logic and counters.
3. Cross-run reuse is observable in live-run trace (`reused_total > 0`) when proposal semantics unchanged.
4. Proposal review/apply flows remain backward-compatible with existing `proposal_id` endpoint contracts.
