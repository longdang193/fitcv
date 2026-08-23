---
template_id: implementation-plan
artifact_type: plan
status: completed
layer: change
name: fitcv-candidate-profile-restore-revision
targets:
  - src/fitcv_cp/sqlite_store.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - docs/superpowers/plans/2026-08-23-00-00-fitcv-candidate-profile-restore-revision-plan.md
---

# FitCV Candidate Profile Restore/Revision Patch Plan

## Goal

Repair lifecycle-only Candidate Profile revision persistence so archive and
restore preserve canonical payload, history, eligibility, and Run snapshots.

## Implementation Outcomes

### Lifecycle revision continuity

Archive/restore lifecycle transitions create durable successor revision rows
containing the prior canonical payload, while historical rows remain unchanged.

### Projection and Run safety

Detail projections expose canonical payload after restore, `use_for_run` is false
when payload resolution fails, and strict Run snapshot creation resolves the
restored current revision.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Executor: `codex`
- Required skills: `skill-executing-plans`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: declared store/test edits, focused tests, isolated disposable schema-5 live validation, read-only independent validation
- User-approval actions: commit, push, full 25-probe suite, Redis/Docker changes, sample-data changes
- Parallel ownership: `none`
- Sequential fallback: `red test`, minimal store fix, focused proof, live proof, independent validator

## Coordination State

- Coordination owner: `single lead controller`
- Branch: `main`
- Base commit: `441d9bb4c611ea025c407a2af68b3c1a1aa4ed6d`
- Active task(s): `none`
- Expected workspace: `main` with preserved pre-existing source/test and sample-data changes
- Next action: commit and push authorized verified workspace state
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | red regression, green focused tests, direct SQLite proof, live lifecycle + Run snapshot proof, independent validator PASS | `586 passed`; live schema 5/integrity ok; validator PASS |

## Task Breakdown

### Task 1: Repair lifecycle revision persistence

**Purpose:**
- Preserve canonical Profile content through archive/restore and prove restored Run eligibility.

**Task Function:**
- Implement and validate narrow backend persistence fix.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: coupled SQLite revision invariant, API projection, and strict Run snapshot behavior.

**Validator Profile:**
- Controller-selected: `high`
- Selection basis: independent source, SQLite, regression, and live lifecycle validation.

**Specification Coverage:**
- Current `candidate_profiles.revision` resolves to exactly one durable revision row.
- Lifecycle transitions preserve canonical JSON, checksum, schema version, and historical rows.
- Active Profiles are run-eligible only when canonical payload resolves.

**Required Skills:**
- `skill-test-driven-development`
- `skill-backend-verification`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect/modify: `src/fitcv_cp/sqlite_store.py: _candidate_profile_resource`, `transition_candidate_profile_lifecycle`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: schema-5 disposable SQLite database and `create_run_bundle`

**Dependencies:**
- Accepted bootstrap commit remains base.
- Existing P0 recovery plan and preserved sample-data changes remain untouched.

**Authority:**
- Preauthorized local actions: declared source/test edits and bounded validation.
- Stop for: plan/Git mismatch, out-of-scope changes, missing runtime/provider dependency, or destructive cleanup.

**Steps:**
- [x] Add failing lifecycle/revision/Run snapshot regression.
- [x] Patch canonical SQLite lifecycle owner minimally.
- [x] Run focused tests and direct backend proof.
- [x] Run fresh disposable live lifecycle sequence.
- [x] Obtain independent validator PASS and reconcile Plan/Git.

**Verification:**
- [x] Focused lifecycle tests pass.
- [x] SQLite shows revision rows 1..N with unchanged historical payloads.
- [x] Restored detail has non-null `overview` and `profile`; `use_for_run` is true.
- [x] Strict Run snapshot references restored revision ID/checksum/payload.
- [x] Independent validator returns `PASS`.

**Exit Criteria:**
- All required invariants and proof pass without modifying unrelated changes or running the 25-probe suite.

**Accepted Evidence:**
- Red regression reproduced missing payload before fix.
- `pytest -q tests/test_fitcv_cp/test_sqlite_store.py -k lifecycle_preserves_revision_payload_and_run_snapshot` → `1 passed`.
- `pytest -q tests/test_fitcv_cp/test_sqlite_store.py -k candidate_profile` → `22 passed`.
- `pytest -q tests/test_fitcv_cp/test_app.py -k candidate_profile` → `26 passed`.
- `pytest -q tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py` → `586 passed`.
- `python -m compileall -q src tests` and `git diff --check` passed.
- Live evidence: `C:\tmp\fitcv-profile-lifecycle-20260823\lifecycle-run-evidence.json`; schema `5`, integrity `ok`, revisions `1..4`, restored projection present, Run snapshot payload/checksum/revision match.
- Live API boundary: `GET /candidate-profiles/profile_666bdad8620346be8367ef16d6a91fe6` returned HTTP `200`, revision `4`, non-null `overview`/`profile`, and `use_for_run=true` against the same disposable DB.
- Independent DeepAgents validator returned `PASS`; its focused pytest attempt was blocked by launcher shell allow-list, covered by local full-suite proof.
- Recurring Windows temp SQLite cleanup warning occurs after successful app-test exit; no test failure or repository mutation.

## Verification

- `pytest -q tests/test_fitcv_cp/test_sqlite_store.py -k candidate_profile`
- `python -m compileall -q src tests`
- `git diff --check`
- Fresh disposable schema-5 lifecycle and Run snapshot probe

## Completion Criteria

1. Lifecycle revision continuity is proven by regression and direct SQLite evidence.
2. Restored Profile projection and Run snapshot are proven.
3. Independent validation returns `PASS`.
4. Plan state, Git state, and preserved unrelated changes reconcile.
5. No full P0 probe suite, Redis/Docker, or sample-data changes occur.
