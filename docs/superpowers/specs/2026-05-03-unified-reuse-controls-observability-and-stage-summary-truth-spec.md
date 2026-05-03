# 2026-05-03 Unified Reuse Controls, Observability, and Stage-Summary Truth Spec

## Metadata
- Date: 2026-05-03
- Owner surfaces:
  - `src/fitcv/pipeline.py`
  - `src/fitcv_cp/worker_job.py`
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/settings_schema.py`
  - `src/fitcv_cp/templates/run_detail.html`
- Type: reliability + operator-controls + observability contract hardening
- Severity: high

## Problem Statement
Current runtime behavior has three reliability gaps:
1. Timeline event summaries can diverge from stage artifact truth (example: enrich shown as `0` while artifact has `10` reused rows).
2. Reuse control semantics are inconsistent across expensive stages.
3. Reuse diagnostics are fragmented, making drift/root-cause analysis harder.

## Goals
1. Enforce stage summary truth: event/timeline copy must derive from stage artifacts only.
2. Introduce unified ON/OFF reuse controls for key stages.
3. Standardize reuse observability fields and reason taxonomy across stages.
4. Reduce queue starvation risk by separating production/test queue lanes.

## Non-Goals
1. Changing ranking logic quality thresholds.
2. Redesigning enrichment extraction taxonomy.
3. Changing existing run status enums in this patch.

## Scope
- In scope:
  - stage summary source-of-truth alignment
  - reuse toggle settings + runtime enforcement
  - stage reuse observability schema
  - queue lane routing safeguards
- Out of scope:
  - full queue orchestration redesign
  - external monitoring systems

## Proposed Contract

### 1) Stage summary truth alignment
For timeline/event stage summaries (notably `enrich`), compute message values directly from persisted stage artifact fields:
- `input_counts`
- `output_counts`
- `decision_summary`

No parallel recompute path for operator-facing counts.

### 2) Unified reuse toggles
Add stage-scoped booleans (defaults true):
- `enrich_reuse_enabled`
- `ai_score_reuse_enabled`
- `evidence_reuse_enabled`
- `cv_analysis_reuse_enabled`
- `cv_generation_reuse_enabled`

### 3) Shared smart reuse guard
Reuse only when fingerprint-compatible:
1. input bundle fingerprint
2. stage contract fingerprint (prompt/model/schema/config)
3. relevant candidate/runtime overlay fingerprint when applicable

If mismatch:
- force fresh compute
- record mismatch reason in observability payload

### 4) Unified stage reuse observability schema
Each stage artifact should include additive keys:
- `reuse_enabled` (bool)
- `reuse_attempted` (bool)
- `reused_count` (int)
- `fresh_count` (int)
- `reuse_reason` (`fingerprint_match|fingerprint_mismatch|reuse_disabled|not_applicable`)
- `reuse_fingerprint` (string|null)

### 5) Queue lane separation
Prevent test starvation of operator runs:
- Production queue: `fitcv`
- Test queue: `fitcv-test`
- Route pytest/temp-path jobs to test queue.

## Acceptance Criteria
1. Enrich timeline summary equals enrich stage artifact counts in all runs.
2. Reuse toggles can be switched ON/OFF per stage via settings and are honored.
3. Fingerprint mismatches force fresh path with explicit reason.
4. Stage artifacts expose standardized reuse fields.
5. Test jobs no longer block production queue by default.

## Test Plan

### Unit tests
1. Stage summary formatter uses artifact-only values.
2. Reuse policy matrix for each stage (`enabled` + fingerprint match/mismatch).
3. Reason mapping coverage for reuse outcomes.

### Integration/control-plane tests
1. Enrich event message matches stage artifact counts.
2. Toggle OFF forces fresh path for each stage.
3. Toggle ON + matching fingerprint reuses.
4. Queue routing sends pytest/temp jobs to `fitcv-test`.

## Rollout
1. Wave 1: enrich stage-summary truth fix.
2. Wave 2: shared reuse policy layer + enrich/ai_score/evidence toggles.
3. Wave 3: cv_analysis/cv_generation toggles and observability parity.
4. Wave 4: queue lane split and operational guardrails.

## Risks
1. Fingerprint strictness may lower reuse rate.
2. Partial rollout may temporarily create mixed observability coverage.
3. Queue split requires deploy-time worker config alignment.

## Done Criteria
1. No operator-visible stage count drift from artifacts.
2. Unified reuse controls available and enforced for target stages.
3. Reuse diagnostics are consistent and auditable across stages.
4. Production runs are no longer starved by test queue volume.
