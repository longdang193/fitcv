---
layer: change
artifact_type: spec
status: completed
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-analysis-grounding
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - tests/test_fitcv_cp/test_app.py
related_features: []
related_stages: []
---

# 2026-05-03 Agentic CV Review Lifecycle Truth + Clarity + Batch Actions Spec

## Metadata
- Date: 2026-05-03
- Owner surface: `src/fitcv_cp/` + late-stage review diagnostics in `src/fitcv/`
- Type: lifecycle bugfix + UX contract clarification + operator throughput improvement
- Trigger: review-required ranked outcomes in staged/manual runs
- Severity: high (false-success terminalization + ambiguous operator workflow)

## Problem Statement
Three operator-facing defects exist in the current review-required flow:

1. False-success terminalization:
   - `cv_review_action='approve'` can transition run to succeeded (`cv_review_completed`) even when no new/accepted CV artifact exists for those review-required rows.
   - This breaks run lifecycle truth.

2. Ambiguous review-required message:
   - Message such as `Unsupported requirements require review: ...` does not clearly tell operator what exactly must be reviewed (input vs generated CV vs policy decision).

3. Missing batch operations for Agentic Review Queue:
   - Operators must action review-required rows one-by-one, reducing throughput and consistency.

## Goals
1. Enforce lifecycle truth: run success must not be inferred from review clicks alone.
2. Make review-required diagnostics explicit about review target and expected operator decision.
3. Add safe batch actions to Agentic Review Queue with auditability.

## Non-Goals
1. Changing reranker fit-gate policy.
2. Redesigning CV generation models/prompts.
3. Implementing full collaborative content editor in review UI.

## Scope
- In scope:
  - CV review action semantics and run terminalization gates.
  - Review-required reason payload clarity and wording.
  - Batch action endpoint + UI + audit records for review queue.
- Out of scope:
  - Reworking synonym proposal triage.
  - Provider-level retry-policy redesign (unless needed for explicit regenerate execution path).

## Defect Definitions

### A) False-success on review action
Current issue:
- Queue pending is derived from action presence, and run can be marked succeeded when pending reaches zero.
- This can occur without accepted CV artifacts being produced/persisted.

Required invariant:
- `RunStatus.SUCCEEDED` must require terminal review resolution state that is artifact-truthful.

### B) Ambiguous unsupported-requirements review message
Current issue:
- Free-text message provides unsupported requirements list but not review target or required decision.

Required invariant:
- Every review-required row must state:
  - review target (`cv_output`, `requirements_alignment`, etc.)
  - reason code
  - operator decision options

### C) No batch actions
Current issue:
- Single-row actions only.

Required invariant:
- Batch actions support selected rows with deterministic per-row outcomes and audit.

## Proposed Patch

### 1) Lifecycle contract hardening for review-required closure
Introduce explicit row-level review resolution model for review-required rows:
- `resolution_status` enum:
  - `pending`
  - `approved_as_is`
  - `rejected`
  - `regeneration_requested`
  - `regenerated_and_accepted`
  - `regenerated_and_rejected`

Run may transition from `awaiting_review` to `succeeded` only when:
1. all review-required rows are in a terminal resolution state:
   - `approved_as_is` OR `rejected` OR `regenerated_and_accepted` OR `regenerated_and_rejected`
2. and no row remains `pending` or `regeneration_requested`.

Important:
- `approve` action alone must not imply CV artifact creation.
- `approved_as_is` means operator accepts no-new-CV outcome intentionally.
- Results ledger/status text must reflect this explicit operator acceptance path.

### 2) Clarify review-required diagnostics and message semantics
Replace ambiguous statement-only copy with structured payload + explicit UI text.

Required fields per review-required row:
- `review_required_reason_code` (existing normalized enum)
- `review_target` (new):
  - `cv_output`
  - `requirements_alignment`
  - `validation_guardrail`
  - `other`
- `operator_prompt` (new): one-line actionable guidance
- `unsupported_requirements` (optional array, normalized)

For `unsupported_requirement_gap`, operator-facing text must read as:
- "Review required: generated CV may not cover required stack items. Review the CV output against listed requirements and choose approve, regenerate once, or reject."

Keep detailed raw provider/validator text in debug payload, not primary operator copy.

### 3) Agentic Review Queue batch actions
Add batch action support in run detail:
- actions:
  - `approve_as_is`
  - `regenerate_once`
  - `reject`
- scope:
  - selected rows only (phase 1)

Batch contract:
- request carries list of `job_url` keys + action + actor + optional note
- response persists per-row action results with:
  - `applied`
  - `skipped` (ineligible/duplicate)
  - `failed` (error)
- append one summary event + per-row audit entries

Safety rules:
- dry-run preview of affected count before apply
- idempotent action behavior for repeated submissions
- batch `regenerate_once` sets row to `regeneration_requested` (not terminal)

## Data/Artifact Contract Updates
1. `cv_generation_debug_json` review rows add:
   - `resolution_status`
   - `review_target`
   - `operator_prompt`
   - optional `unsupported_requirements[]`
2. HITL review audit export includes batch summary block:
   - `batch_action_id`
   - `attempted_count`
   - `applied_count`
   - `skipped_count`
   - `failed_count`
3. Run terminalization event should include closure basis:
   - `closure_mode`: `all_review_rows_terminal`
   - `review_required_total`
   - `approved_as_is_total`
   - `rejected_total`
   - `regenerated_total`

## UI Changes
1. Review queue row shows:
- reason code
- review target
- actionable guidance
- current resolution status badge

2. Add batch selection controls + batch action bar.

3. Completion banner text must distinguish:
- "resolved by accepted regenerated CV"
- "resolved by operator accept-as-is/reject decisions"

## Acceptance Tests
1. Route test: single `approve_as_is` on last pending row transitions run to succeeded with explicit closure mode, even with no new CV artifact.
2. Route test: `regenerate_once` keeps run in awaiting-review until regenerate outcome is terminalized.
3. Route test: `approve` legacy action is mapped safely (`approve_as_is`) and does not imply generated artifact.
4. UI test: unsupported-requirements row displays review target and actionable prompt.
5. Batch route test: mixed rows return deterministic applied/skipped/failed counts.
6. Audit test: batch action writes summary + per-row entries.
7. Regression: no path marks succeeded while any review-required row is unresolved.

## Rollout / Verification
1. Targeted tests:
- `tests/test_fitcv_cp/test_app.py -k "cv_review_action or hitl_review"`
- `tests/test_fitcv_cp/test_worker_job.py -k "review_required"`
2. Live smoke:
- trigger run with known review-required rows
- execute: one `regenerate_once`, verify run remains awaiting-review
- resolve all rows via terminal actions, verify then succeeded
3. Artifact check:
- download hitl audit JSON and confirm new closure + batch fields.

## Risks
1. Legacy action compatibility (`approve`) may need migration mapping.
2. Existing dashboards may assume success implies CV artifact creation.
3. Batch action misuse risk without confirmation/preview.

## Open Questions
1. Should `approve_as_is` require mandatory operator note for audit quality?
2. Should batch regenerate support throttling/concurrency cap per run?
3. Should `unsupported_requirements` be capped to avoid noisy UI strings?

## Done Criteria
1. No false-success from non-terminal review actions.
2. Review-required messaging explicitly states review target and decision.
3. Batch actions are available, audited, and idempotent.
4. Tests cover lifecycle truth + batch edge cases.
5. Live run confirms expected awaiting-review -> succeeded progression.
