---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: cross-stage-reuse-symmetry-unified-contract-plan
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-cross-stage-cache-safety
parent_spec: docs/superpowers/specs/2026-05-21-23-45-cv-generation-decision-reuse-symmetry-spec.md
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/app.py
  - src/fitcv/reuse.py
  - tests/
  - docs/api.md
related_features:
  - pipeline_performance
  - trigger_run_management
  - cv_system
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Eliminate near-zero reuse caused by cross-stage design asymmetry by introducing one symmetry-first reuse contract across `enrich`, `ranking`, `cv_analysis`, `synonym_triage`, and `cv_generation`, while preserving correctness constraints and existing observability guarantees.

## Key Deliverables

### Unified Reuse Eligibility Contract

Implement one shared reuse eligibility policy (`succeeded_or_checkpointed`) and one shared decision schema consumed by all five stages so stage behavior differs only where domain-required (match mode), not by hidden lifecycle gates.

### Cross-Stage Snapshot Reuse Path

Extend reusable snapshot collection and indexing to include checkpoint-stage artifacts for non-terminal runs (`awaiting_continue`) so repeated overlapping runs can reuse late-stage results instead of re-computing from scratch.

### Symmetric Observability And Diagnostics

Standardize per-stage reuse telemetry (`reused`, `fresh`, `rate`, `not_eligible`, `reason_code`) and expose anomaly diagnostics when overlap exists but reuse drops below floor.

### Verification Coverage

Add deterministic integration tests and targeted scenario tests proving reuse recovery across overlapping runs and preserving existing correctness/validation behavior.

## Task/Wave Breakdown

### Task 1: Define Unified Reuse Contract And Policy Surfaces

**Purpose:**
- Establish one canonical reuse contract shape and defaults for all stages.

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv/reuse.py` (new or existing shared module)
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/`

**Preconditions:**
- Current asymmetry findings confirmed in latest debugging evidence.
- Existing run-mode + synonym-management controls remain backward compatible.

**Steps:**
- [x] Step 1: Define shared reuse policy schema with stage entries (`enabled`, `source_scope`, `match_mode`).
- [x] Step 2: Set symmetry defaults: all stages `source_scope=succeeded_or_checkpointed`; `match_mode=exact` for `enrich/ranking/cv_analysis/cv_generation`; `exact_or_core` for `synonym_triage`.
- [x] Step 3: Implement shared decision envelope (`decision`, `reason_code`, `fingerprint`, `source_run_id`, `source_artifact_type`).
- [x] Step 4: Keep legacy flags compatible via adapter mapping and explicit deprecation comments.

**Verification:**
- [x] Unit test policy normalization and backward-compat mapping.
- [x] Assertions that each stage resolves a non-null policy entry.

**Exit Criteria:**
- All five stages read policy through one shared contract API.

### Task 2: Unify Snapshot Eligibility And Source Collection

**Purpose:**
- Remove lifecycle gate asymmetry that starves late-stage reuse.

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/`

**Preconditions:**
- Task 1 contract API available.

**Steps:**
- [x] Step 1: Refactor `_collect_late_stage_reuse_snapshots` to include checkpoint-derived snapshots when policy allows (`succeeded_or_checkpointed`).
- [x] Step 2: Include reusable payloads from stage-transition artifacts (ranking/cv-analysis/cv-generation/synonym triage where applicable).
- [x] Step 3: Keep strict parsing guards for malformed prior payloads and log normalized skip reasons.
- [x] Step 4: Thread unified snapshot bundle into `run_pipeline(...)` unchanged for current callsites.

**Verification:**
- [x] Integration test: prior run in `awaiting_continue` contributes reusable late-stage rows.
- [x] Integration test: malformed snapshot payload is skipped safely with warning, no crash.

**Exit Criteria:**
- Late-stage indexes are hydrated from both succeeded exports and eligible checkpoint sources.

### Task 3: Stage Adapters For Symmetric Reuse Decisions

**Purpose:**
- Apply shared contract without breaking stage-specific correctness.

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/`

**Preconditions:**
- Tasks 1–2 complete.

**Steps:**
- [x] Step 1: Ranking adapter uses shared decision envelope; keep exact fingerprint semantics.
- [x] Step 2: CV analysis adapter uses shared decision envelope; preserve reranker skip behavior.
- [x] Step 3: CV generation adapter keeps artifact + decision reuse semantics but reports through shared envelope.
- [x] Step 4: Synonym triage adapter keeps strict/core logic but emits same decision schema.
- [x] Step 5: Enrich adapter emits same decision schema and reason codes for fresh/reused/not-eligible paths.

**Verification:**
- [x] Tests assert decision schema shape is identical across stage outputs.
- [x] Regression test confirms unchanged acceptance/validation outcomes for cv-generation.

**Exit Criteria:**
- Reuse decision data is structurally symmetric across all five stages.

Progress notes (2026-05-22 lane execution checkpoint):
- Structural blocker in `src/fitcv/pipeline.py` was remediated by restoring function boundaries between `_build_stage_transition_artifacts` and `_build_cv_generation_input_fingerprint`.
- Regression proof after structural fix:
  - `python -m pytest -q tests/test_pipeline.py -k "reuses_exact_match_cv_analysis_records"` -> passed
  - `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py -k "reuse or snapshot or late_stage"` -> passed

### Task 4: Symmetric Metrics + Near-Zero Anomaly Guard

**Purpose:**
- Detect and explain near-zero reuse rather than silently wasting compute.

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/`

**Preconditions:**
- Task 3 adapters emit shared decision envelope.

**Steps:**
- [~] Step 1: Emit standardized per-stage reuse metrics (`fresh`, `reused`, `rate`, `not_eligible`).
- [x] Step 2: Add configurable reuse floor guard for overlap scenarios (default warning-only).
- [x] Step 3: Emit `reuse_anomaly` event with reason-code histogram when floor breached.
- [x] Step 4: Surface same metrics/hints in run detail UI for all stages.

**Verification:**
- [x] Scenario test with overlap and intentional mismatch triggers anomaly event.
- [x] UI payload tests verify consistent metric keys per stage.

**Exit Criteria:**
- Near-zero events are observable with explicit root-cause breakdown.

### Task 5: Docs, Contracts, And Rollout Safety

**Purpose:**
- Keep source-of-truth docs and rollout controls aligned.

**Files:**
- Modify: `docs/api.md`
- Modify: `configs/` (if policy defaults stored there)
- Modify: `docs/superpowers/execution_context_packs/<lane-id>/latest.md`
- Verify: validators

**Preconditions:**
- Tasks 1–4 complete.

**Steps:**
- [x] Step 1: Document unified reuse contract, reason codes, and metrics in `docs/api.md`.
- [x] Step 2: Add rollout flag guidance and default profile behavior.
- [x] Step 3: Update lane execution context pack with implemented contract and verification evidence.
- [x] Step 4: Ensure plan/context-pack synchronization notes capture final behavior deltas.

**Verification:**
- [x] `python scripts/validate_planning_lifecycle.py --strict`
- [x] `python scripts/validate_checkpoint_packs.py`
- [x] `python scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- Docs and governance artifacts describe same runtime contract as code.

## Verification

- `python -m pytest tests -k "reuse or synonym or cv_analysis or ranking or cv_generation"`
- `python scripts/validate_planning_lifecycle.py --strict`
- `python scripts/validate_checkpoint_packs.py`
- `python scripts/validate_repo_contracts.py --fast`
- Live-run replay on overlapping datasets to confirm reuse rate recovery and stable outcomes.

Latest live evidence (2026-05-22):
- Overlap run pair reuse recovered from near-zero to full reuse in synonym triage:
  - `cbaa0054-67f3-4084-8718-145ef0cfa9cc` / `eb184e11-2df1-403c-aaa2-b74459a71ce9` (AI50): reused_total=22, fresh_total=0
  - `6837fa7f-dcf1-44d5-942b-1ac21a0d76c0` / `babf8fb6-8fb5-4186-b90d-9b9528afb35a` (data50): reused_total=9, fresh_total=0
- Provider auth drift (401) verified resolved in current runtime:
  - fresh runs show `generation_failed=0` and `unauthorized_401=0`
- Review-gated closure completed:
  - `9d08dcdd-1692-484e-84fe-4008ce1449f5`: finalized=5, `cvs_generated=5`, status `succeeded`
  - `b7db38f7-7236-43b4-ace8-02f21411879f`: finalized=8, `cvs_generated=8`, status `succeeded`

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
