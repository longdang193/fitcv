# 2026-05-03 Agentic CV Review Lifecycle Truth + Clarity + Batch Actions Implementation Execution Map

Spec reference:
- `docs/superpowers/specs/2026-05-03-agentic-cv-review-lifecycle-truth-clarity-batch-actions-spec.md`

## Objective

Implement review-required lifecycle hardening and operator UX upgrades by:
- preventing false-success terminalization from action clicks alone,
- making unsupported-requirements review prompts explicit and actionable,
- adding batch actions to Agentic Review Queue with audit-safe outcomes.

## Constraints

- No reranker or fit-gate policy changes.
- Preserve backward compatibility for existing stored review actions where feasible.
- Keep patch additive and bounded to review-required lifecycle + UI + audit paths.

## Wave Plan

## Wave 1: Lifecycle Truth Guard (No False Success)

### Tasks

1. Introduce explicit review row resolution semantics in review queue derivation:
   - terminal: `approved_as_is`, `rejected`, `regenerated_and_accepted`, `regenerated_and_rejected`
   - non-terminal: `pending`, `regeneration_requested`
2. Update run completion gate in `/admin/runs/{run_id}/cv-review-action` flow:
   - run can become succeeded only when all review rows are terminal
   - never infer CV artifact generation from `approve` action
3. Keep compatibility mapping:
   - legacy `approve` action maps to `approved_as_is` resolution
   - legacy `reject` maps to `rejected`

### Files (expected)

- `src/fitcv_cp/app.py`
- `tests/test_fitcv_cp/test_app.py`

### Validation

- `approve_as_is` on final pending row can close run with explicit operator-accept closure semantics.
- `regenerate_once` does not close run.
- no path marks succeeded while any row remains unresolved.

## Wave 2: Review-Required Clarity Contract

### Tasks

1. Extend review-required row payload construction to include:
   - `review_target`
   - `operator_prompt`
   - optional normalized `unsupported_requirements[]`
2. Replace ambiguous unsupported-requirements message in operator surface with explicit guidance:
   - review target = CV output vs requirement alignment
   - actionable choice list: approve-as-is / regenerate-once / reject
3. Keep raw low-level error text in debug payload but not as primary operator instruction.

### Files (expected)

- `src/fitcv/pipeline.py` (message normalization surface)
- `src/fitcv_cp/app.py` (review payload shaping)
- `src/fitcv_cp/templates/run_detail.html`
- `tests/test_pipeline.py`
- `tests/test_fitcv_cp/test_app.py`

### Validation

- review rows with `unsupported_requirement_gap` show explicit review target and operator prompt.
- reason-code mapping remains stable for existing runs.

## Wave 3: Agentic Review Queue Batch Actions

### Tasks

1. Add batch review action endpoint for selected `job_url` rows:
   - action options: `approve_as_is`, `regenerate_once`, `reject`
2. Implement deterministic per-row result ledger:
   - `applied`, `skipped`, `failed`
3. Persist audit trail:
   - one batch summary event
   - row-level action entries with actor/note/timestamp
4. Add run-detail UI controls for row selection + batch action submission.

### Files (expected)

- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/run_detail.html`
- `tests/test_fitcv_cp/test_app.py`

### Validation

- batch action executes selected rows only.
- repeated submission is idempotent (skips already terminal rows).
- audit payload contains summary counts and row entries.

## Wave 4: Audit/Export Contract + Regression Hardening

### Tasks

1. Extend HITL audit payload with closure-basis summary:
   - closure mode
   - totals by terminal resolution bucket
2. Ensure run terminal event (`cv_review_completed`) includes closure basis context.
3. Add regression tests covering:
   - false-success prevention
   - closure after all rows terminal
   - mixed batch outcomes

### Files (expected)

- `src/fitcv_cp/app.py`
- `tests/test_fitcv_cp/test_app.py`

### Validation

- `cv_review_completed` emitted only under valid terminal conditions.
- hitl audit export reflects batch + resolution metadata.

## Live Verification Checklist

Use a fresh staged run that yields review-required rows:

1. Trigger `regenerate_once` for one row:
   - run remains `awaiting_review`
2. Use batch `approve_as_is` or `reject` on remaining unresolved rows:
   - run transitions to `succeeded` only when all terminal
3. Inspect run timeline:
   - no misleading success message before full terminal resolution
4. Inspect HITL audit export:
   - summary counts reconcile with queue row statuses and actions

## Validation Commands

- `pytest -q tests/test_fitcv_cp/test_app.py -k "cv_review_action or hitl_review"`
- `pytest -q tests/test_pipeline.py -k "review_required_reason_code or unsupported"`

Note: if unrelated suite drift exists, use focused slices above plus live run verification.

## Rollout

1. Merge Wave 1 first (lifecycle truth blocker).
2. Merge Wave 2 + Wave 3 together if UI/contract coupling is tight.
3. Validate on one historical run + one fresh run before declaring fixed.

## Exit Criteria

- No run is marked succeeded from non-terminal review actions.
- Review-required unsupported-requirements messaging is explicit and actionable.
- Agentic Review Queue supports safe batch actions with full auditability.
