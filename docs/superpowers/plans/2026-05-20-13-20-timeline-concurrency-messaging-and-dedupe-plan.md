---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: timeline-concurrency-messaging-and-dedupe
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-05-17-00-20-event-timeline-semantic-outcome-dedup-spec.md
targets:
  - src/fitcv_cp/app.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/templates/run_detail.html
  - tests/test_fitcv_cp/test_app.py
  - tests/test_pipeline_agentic_late_stage.py
related_features:
  - admin_control_plane_core
  - pipeline_performance
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Make Event Timeline progress rows deterministic and operator-readable by collapsing duplicate heartbeat/progress noise and surfacing effective concurrency settings for all concurrency-applied stages.

## Key Deliverables

### Deliverable 1

Event Timeline deduplicates repeated `Enrich In Progress` heartbeat rows based on display-equivalent content, so repeated rows do not spam timeline while preserving meaningful phase transitions.

### Deliverable 2

Timeline stage summary messages include effective concurrency context for each stage that applies concurrency (`enrich`, `ranking`, `cv_analysis`, `cv_generation`) using stable message schema and fallback behavior when field is absent.

### Deliverable 3

Tests cover dedupe semantics, concurrency message rendering, and regression protection for run detail timeline presentation.

## Task/Wave Breakdown

### Task 1: Define canonical timeline concurrency evidence contract

**Purpose:**
- Standardize payload fields that timeline renderer can trust across stages.

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`

**Preconditions:**
- GitNexus index refreshed and source-first symbol mapping confirmed.

**Steps:**
- [x] Identify existing event payload keys emitted for `enrich_heartbeat`, ranking completion, cv analysis progress, cv generation start/result.
- [x] Add/normalize explicit effective-concurrency fields in emitted payload snapshots for all concurrency-applied stages (preserve backward compatibility when unavailable).
- [x] Ensure payload field naming is stable and stage-local (`*_concurrency_effective` or equivalent canonical key).

**Verification:**
- [x] Targeted pipeline tests assert emitted payload contains effective concurrency for each applicable stage.

**Exit Criteria:**
- Timeline renderer can read a single deterministic concurrency field per applicable stage without guessing from config text.

### Task 2: Collapse duplicate Enrich In Progress rows by display fingerprint

**Purpose:**
- Prevent timeline spam while preserving meaningful enrich progress milestones.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 payload contract decided.

**Steps:**
- [x] Refine `_collapse_timeline_noise` for `enrich_heartbeat` to collapse consecutive display-equivalent rows (stage label + level + rendered message).
- [x] Preserve phase-change rows (`batch_start`, `batch_progress`, `batch_done`) when rendered summary differs.
- [x] Keep repeat counter semantics consistent with existing collapsed-row UI.

**Verification:**
- [x] Add/adjust tests proving duplicate enrich heartbeat rows collapse and non-equivalent heartbeat rows remain distinct.

**Exit Criteria:**
- Repeated heartbeat noise is trimmed, but real state transitions stay visible.

### Task 3: Add concurrency context to timeline stage messages

**Purpose:**
- Expose runtime concurrency settings directly in operator timeline messages.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 payload keys available in stage events.

**Steps:**
- [x] Update `_timeline_stage_summary_message` for `enrich_heartbeat` to append effective concurrency.
- [x] Extend ranking/cv_analysis/cv_generation summary branches to append concurrency when present.
- [x] Keep concise fixed field order in messages for scanability and deterministic test assertions.

**Verification:**
- [x] Add tests asserting message contains concurrency for applicable stage events and degrades gracefully when missing.

**Exit Criteria:**
- Operators can see applied concurrency directly in timeline without opening settings.

### Task 4: Run bounded regression and UX sanity checks

**Purpose:**
- Ensure timeline change does not regress review/synonym flows or stage artifact links.

**Files:**
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`

**Preconditions:**
- Tasks 1-3 complete.

**Steps:**
- [x] Run focused timeline + pipeline concurrency pytest slices.
- [x] Run fast repo validator hook.
- [x] Perform manual run-detail spot check to confirm duplicated enrich heartbeat rows are trimmed and concurrency text appears.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_app.py -k "timeline and (enrich or cv_analysis or cv_generation or ranking)"`
- [x] `pytest -q tests/test_pipeline_agentic_late_stage.py -k "emits_effective_concurrency_for_enrich_and_ranking_events"`
- [x] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- Automated and manual evidence confirms timeline clarity improvement and no bounded regressions.

## Verification

- `pytest -q tests/test_fitcv_cp/test_app.py -k "timeline and (enrich or cv_analysis or cv_generation or ranking)"`
- `pytest -q tests/test_pipeline_agentic_late_stage.py -k "emits_effective_concurrency_for_enrich_and_ranking_events"`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
