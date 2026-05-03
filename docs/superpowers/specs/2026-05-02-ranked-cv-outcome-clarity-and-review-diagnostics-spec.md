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

# 2026-05-02 CV Output Outcome Clarity + Review-Required Diagnostics Patch Spec

## 1) Problem Statement

Run `28c75b85-507c-427f-b6b5-0a30321627f1` shows `ranked=4`, `cvs_generated=0`, and the operator-facing narrative implies all 4 failed CV output.
Live artifacts prove this is conflating distinct outcomes:

- 2 rows: `blocked_by_reranker_fit` (CV generation not attempted)
- 2 rows: `review_required` (generation accepted but held for HITL)

Also, `cv-generation-review-required.json` has weak diagnostics:

- `reason_code: "unknown"` for all rows
- `request_id: ""`

This reduces observability and creates false “bug” impressions.

## 2) Goals

1. Make ranked CV outcomes operator-clear and non-misleading.
2. Populate structured review-required reason taxonomy (avoid `unknown` where determinable).
3. Improve traceability by filling provider request identifiers when available.
4. Keep behavior/policy unchanged (no ranking/generation logic change), only diagnostics + reporting quality.

## 3) Non-Goals

- No change to reranker fit thresholds or gating policy.
- No change to review gate strictness.
- No relaxation of quality/safety checks.
- No model/provider switch.

## 4) Scope

### In scope

- Outcome classification and display labels in run summaries/exports/detail.
- Review-required reason-code extraction/mapping.
- Request ID propagation into review-required export rows.
- Tests for new outcome buckets and reason-code mapping coverage.

### Out of scope

- New UI pages.
- Backfilling old historical runs (unless already supported naturally by recompute endpoints).

## 5) Proposed Changes

## A. Outcome bucket clarity for ranked rows

### Current ambiguity

Single statement like “X ranked jobs did not produce valid CV output” lumps:

- fit-gated skips
- review-required holds
- true failures

### Patch

Introduce explicit ranked outcome buckets in run-detail summary + export diagnostics:

- `ranked_fit_gated_count` (e.g., `blocked_by_reranker_fit`)
- `ranked_review_required_count` (generation attempted, pending HITL)
- `ranked_generation_failed_count` (actual generation/validation/persistence failure)
- `ranked_cv_created_count`

Display/operator message:

- Replace ambiguous “did not produce valid CV” with structured breakdown.

## B. Review-required reason-code taxonomy mapping

### Current issue

`cv-generation-review-required.json` emits `reason_code: "unknown"` though operator note contains clear cause text.

### Patch

Add deterministic mapping from debug record fields (`error.stage`, `error.message`, known review gate patterns) into stable reason codes.

Initial taxonomy (minimum set):

- `unsupported_requirement_gap`
- `evidence_coverage_insufficient`
- `quality_gate_failed`
- `validation_guardrail_failed`
- `provider_response_unusable`
- `manual_review_other` (fallback only)

Rules:

- Prefer structured fields over free-text when available.
- Keep `manual_review_other` only when no confident mapping exists.
- Include mapped code in debug record + review-required export row.

## C. Provider request ID propagation

### Current issue

`request_id` blank in review-required rows.

### Patch

Populate `request_id` from available runtime trace fields (attempt-level response/request identifiers), if present.

- Keep nullable behavior but no forced empty string.
- Standardize field as `null` when unavailable instead of `""` to reduce ambiguity.

## D. Artifact consistency improvements

Ensure the following artifacts align on outcome semantics:

- `cv-debug.json`
- `cv-generation-review-required.json`
- `export.json` / results ledger summaries
- run detail headline counters

No contradictions between these surfaces.

## 6) Acceptance Criteria

1. For run patterns like `28c75b85-507c-427f-b6b5-0a30321627f1`, summary distinguishes:
   - fit-gated skipped ranked rows
   - review-required ranked rows
   - true failed rows
   - created CV rows
2. `cv-generation-review-required.json`:
   - no `unknown` reason code when cause matches known patterns
   - `request_id` is non-empty when trace provides it; otherwise `null`
3. `cv-debug.json` and `export.json` remain logically consistent with the new counters.
4. Existing pipeline decisions unchanged:
   - same shortlist/ranking/generation gating outcomes for identical inputs.

## 7) Test Plan

1. Unit tests: reason-code mapper
   - message/stage combinations map to expected taxonomy values
   - unknown/unmatched falls back to `manual_review_other`
2. Unit tests: ranked outcome counter builder
   - mixed run with blocked/review-required/failure/success yields correct counts
3. Integration tests: run detail rendering/export payload
   - verifies non-ambiguous summary language and counter presence
4. Regression tests:
   - existing successful CV generation paths unchanged
   - existing reranker-fit skip behavior unchanged

## 8) Rollout & Safety

1. Ship behind additive fields (no schema-breaking removals).
2. Keep legacy fields for compatibility during transition.
3. Validate on one fresh staged run with mixed outcomes.
4. Verify operator-facing copy before broad usage.

## 9) Risks & Mitigations

- Risk: Overfitting text-based mapping.
  - Mitigation: prioritize structured fields and conservative fallback.
- Risk: UI drift from export values.
  - Mitigation: derive all counters from shared helper.
- Risk: Historical runs missing trace IDs.
  - Mitigation: allow `null` gracefully.

## 10) Definition of Done

- Code merged with tests passing.
- Run detail no longer implies false “all ranked failed CV.”
- Review-required rows carry meaningful reason codes.
- Request IDs populated when source trace includes them.
