---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: workstream-bounded-agentic-cv-quality
map_type: implementation_execution
threads:
  - workstream-bounded-agentic-cv-quality.agentic-cv-quality-analysis-grounding
specs:
  - docs/superpowers/specs/2026-05-02-ranked-cv-outcome-clarity-and-review-diagnostics-spec.md
---

# 2026-05-02 Ranked CV Outcome Clarity + Review Diagnostics Implementation Execution Map

Spec reference:
- `docs/superpowers/specs/2026-05-02-ranked-cv-outcome-clarity-and-review-diagnostics-spec.md`

## Objective

Implement operator-trust fixes for ranked CV outcomes by:
- separating fit-gated vs review-required vs true failure outcomes,
- mapping `review_required` rows to stable reason codes,
- propagating provider request IDs when present,
- keeping existing pipeline decision behavior unchanged.

## Constraints

- No ranking/gating policy changes.
- Additive payload changes only (no breaking removals).
- Maintain compatibility with existing run-detail and export consumers.

## Wave Plan

## Wave 1: Shared Outcome Classification Layer

### Tasks

1. Add a shared helper to classify ranked rows into:
   - `ranked_cv_created_count`
   - `ranked_fit_gated_count`
   - `ranked_review_required_count`
   - `ranked_generation_failed_count`
2. Wire helper into run-detail summary builder and export payload builders.
3. Replace ambiguous “did not produce valid CV output” copy with explicit breakdown.

### Files (expected)

- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/run_detail.html`

### Validation

- Run detail for mixed-outcome run shows split counters.
- `export.json` reflects the same counts.

## Wave 2: Review-Required Reason Code Mapping

### Tasks

1. Implement deterministic mapper from structured debug fields:
   - primary inputs: `error.stage`, `error.message`, known review gate signatures.
2. Emit stable taxonomy values:
   - `unsupported_requirement_gap`
   - `evidence_coverage_insufficient`
   - `quality_gate_failed`
   - `validation_guardrail_failed`
   - `provider_response_unusable`
   - `manual_review_other` (fallback only)
3. Use mapper when building `cv-generation-review-required.json`.

### Files (expected)

- `src/fitcv_cp/app.py`

### Validation

- Review-required rows for run `28c75b85-507c-427f-b6b5-0a30321627f1` no longer return `unknown` when patterns match.

## Wave 3: Provider Request ID Propagation

### Tasks

1. Pull request/response IDs from agentic trace attempts when available.
2. Populate `request_id` in review-required rows.
3. Normalize missing IDs to `null` (not empty string).

### Files (expected)

- `src/fitcv_cp/app.py`

### Validation

- `cv-generation-review-required.json` shows populated IDs when trace has them.
- Absent IDs render as `null`.

## Wave 4: Test Coverage + Regression Guardrails

### Tasks

1. Add unit tests for reason-code mapper.
2. Add unit tests for ranked-outcome bucket helper.
3. Add integration-style assertions for run-detail/export consistency.
4. Verify no regressions in existing synonym/review UI paths.

### Files (expected)

- `tests/test_fitcv_cp/test_app.py`

### Validation commands

- `pytest -q tests/test_fitcv_cp/test_app.py -k "cv_generation_review_required or ranked or outcome"`
- Broader sanity slice around run-detail and exports.

## Live Verification Checklist

Use run `28c75b85-507c-427f-b6b5-0a30321627f1`:

1. `GET /admin/runs/{id}/export.json`
   - check split ranked counters and no ambiguous outcome narrative.
2. `GET /admin/runs/{id}/cv-generation-review-required.json`
   - check reason codes are specific (not blanket `unknown`).
   - check `request_id` formatting (`null` or non-empty).
3. `GET /admin/runs/{id}`
   - verify run-detail summary matches export counters.

## Rollout

1. Merge additive payload + UI patch.
2. Validate on one fresh staged run and one historical mixed run.
3. If stable, keep as default behavior.

## Exit Criteria

- Mixed ranked outcomes are clearly and correctly bucketed.
- Review-required diagnostics are actionable and mostly non-`unknown`.
- Request traceability is improved without changing pipeline decisions.
