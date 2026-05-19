---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: cv-review-markdown-integrity-implementation-plan
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-generation-repair
parent_spec: docs/superpowers/specs/2026-05-19-10-48-cv-review-markdown-integrity-spec.md
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - tests/test_fitcv_cp/
  - docs/superpowers/specs/2026-05-19-10-48-cv-review-markdown-integrity-spec.md
related_features: []
related_stages:
  - cv_generation
---

## Goal

Implement approved markdown-integrity spec so HITL `approve_as_is` persists full CV markdown, preview truncation remains display-only, and legacy truncated payloads are blocked with explicit operator-visible reason.

## Key Deliverables

### Deliverable 1: Dual-field debug-record markdown contract implemented

`cv_generation_debug_json` records for review-required rows contain authoritative full markdown and bounded preview markdown with deterministic field precedence for legacy payloads.

### Deliverable 2: Finalize path hardening and compatibility behavior implemented

`_finalize_review_draft_as_cv_artifact` persists only allowed full-markdown sources, blocks truncation sentinels, and returns stable reason codes for all compatibility branches.

### Deliverable 3: Regression and recovery verification coverage implemented

Unit/integration tests prove no truncation leakage into `cv_versions`, queue preview remains bounded, and historical truncated-row recovery workflow behavior is testable.

## Task/Wave Breakdown

### Task 1: Implement debug-record field split at producer boundary

**Purpose:**
- separate persistence-grade markdown from preview-grade markdown at `worker_job` payload construction point

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- approved spec exists: `docs/superpowers/specs/2026-05-19-10-48-cv-review-markdown-integrity-spec.md`
- current truncation behavior confirmed in `_build_cv_generation_debug_payload`

**Steps:**
- [x] Step 1: add dual markdown fields (`markdown_full`, `markdown_preview`) for review-required debug records while retaining legacy compatibility field handling.
- [x] Step 2: apply truncation only to preview field and stop mutating authoritative full field.
- [x] Step 3: keep payload size guard bounded via preview truncation constant and deterministic suffix behavior.

**Verification:**
- [x] targeted unit test: payload builder preserves full markdown and bounds preview markdown
- [x] source inspection confirms no truncation applied to persistence-grade field

**Exit Criteria:**
- debug payload provides clean split between full and preview markdown with no regression for non-review statuses

### Task 2: Implement queue and finalize-path source precedence + sentinel block

**Purpose:**
- enforce safe read precedence and prevent truncated draft persistence in HITL approve actions

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Task 1 complete
- existing queue/finalize call chain mapped (`_build_hitl_review_queue`, `_finalize_review_draft_as_cv_artifact`, batch action endpoint)

**Steps:**
- [x] Step 1: update queue preview assembly to prioritize `markdown_preview`, then bounded derivation from `markdown_full`, then legacy fallback.
- [x] Step 2: update finalize markdown selection precedence: `markdown_full` -> safe legacy `markdown_final` -> missing draft failure.
- [x] Step 3: add truncation sentinel guard (`...[truncated]`, `...[truncated in review queue]`) returning deterministic failure reason `truncated_draft_blocked` and preventing DB write.
- [x] Step 4: ensure action/audit payload paths propagate failure reason without altering existing lifecycle semantics.

**Verification:**
- [x] unit tests for source precedence branches and failure reasons
- [x] integration test for `approve_as_is` path with >4000-char markdown fixture asserts full persistence

**Exit Criteria:**
- approve path cannot persist sentinel-truncated markdown and compatibility behavior is deterministic

### Task 3: Add regression suite and repair-workflow harness

**Purpose:**
- lock behavior with executable proof and define repeatable recovery checks for already-truncated rows

**Files:**
- Inspect: `src/fitcv_cp/bq_store.py`
- Modify: `tests/test_fitcv_cp/` (new/updated tests)
- Verify: `tests/test_fitcv_cp/`, `scripts/hooks/run_validator.py`

**Preconditions:**
- Task 2 complete
- affected rows and sentinel patterns documented from investigation

**Steps:**
- [x] Step 1: add fixture-driven tests for legacy payload handling (safe legacy value, sentinel legacy value, missing draft).
- [x] Step 2: add regression test ensuring queue preview bounded output remains intact with new fields.
- [x] Step 3: add recovery-harness test plan/checks (detect truncated persisted rows, verify regenerated replacement behavior and audit evidence contract).
- [x] Step 4: document rollback notes in plan execution logs: revert field-read precedence change and sentinel guard together if rollback required.

**Verification:**
- [x] run targeted test module(s) for HITL review/finalize paths
- [x] run repo hook subset validator

Execution note:
- Scoped regression tests added for markdown-integrity paths passed (worker/app/bq_store targeted tests).
- Broader filter run `python -m pytest tests/test_fitcv_cp -k "review or truncate or finalize" -q` shows unrelated pre-existing synonym-review UI failures; not introduced by this plan scope.

**Exit Criteria:**
- tests prove no truncation leak path, compatibility preserved, and recovery workflow is verifiable

## Verification

- `python -m pytest tests/test_fitcv_cp -q`
- `python scripts/hooks/run_validator.py --fast`
- optional focused regression run once tests are named: `python -m pytest tests/test_fitcv_cp -k "review or truncate or finalize" -q`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. plan execution handoff references this artifact and parent spec with no unresolved design decisions
