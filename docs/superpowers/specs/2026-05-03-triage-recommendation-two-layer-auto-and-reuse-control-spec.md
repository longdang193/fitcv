# 2026-05-03 Triage Recommendation Two-Layer Auto + Reuse Control Spec

## Metadata
- Date: 2026-05-03
- Owner surfaces:
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/templates/run_detail.html`
  - `src/fitcv/pipeline.py` (or recommendation generation stage owner)
  - settings schema + settings store surfaces
- Type: control-plane behavior + recommendation lifecycle contract
- Severity: medium-high (stale recommendations and operator confusion risk)

## Problem Statement
Triage recommendation behavior currently lacks a clean operator contract separating:

1. whether recommendations should be generated at all, and
2. whether existing recommendations should be reused.

This causes ambiguity, repeated recompute, or stale reuse without explicit policy visibility.

## Goals
1. Provide clear two-layer controls:
   - `auto_triage_recommendation_enabled`
   - `triage_recommendation_reuse_enabled`
2. Keep default behavior cost-efficient and safe.
3. Make reuse decisions observable and auditable.
4. Ensure overlay/policy changes invalidate stale reuse automatically.

## Non-Goals
1. Redesigning recommendation model quality logic.
2. Changing synonym extraction taxonomy itself.
3. Building a new recommendation service.

## Proposed Contract

### Layer 1: Auto Recommendation Generation
Setting:
- `auto_triage_recommendation_enabled` (bool, default `true`)

Meaning:
1. `true`: recommendation stage runs when proposals exist.
2. `false`: recommendation stage is skipped entirely.

### Layer 2: Reuse Control
Setting:
- `triage_recommendation_reuse_enabled` (bool, default `true`)

Meaning:
1. `true`: reuse prior compatible recommendation outputs when valid.
2. `false`: always generate fresh recommendation outputs when auto is on.

### Combined Behavior Matrix
1. auto=`false`, reuse=`false`: no recommendations.
2. auto=`false`, reuse=`true`: no recommendations (reuse ignored because auto layer off).
3. auto=`true`, reuse=`false`: force fresh generation.
4. auto=`true`, reuse=`true`: smart reuse on compatibility match, else fresh generation.

## Compatibility Guard (Smart Reuse)
Reuse must require fingerprint compatibility across:
1. proposal payload hash
2. recommendation policy/version hash
3. synonym overlay fingerprint (skills/domain/role_family)
4. relevant candidate context fingerprint (if used by recommendation logic)

If any mismatch:
1. do not reuse
2. regenerate fresh
3. log mismatch reasons

## Observability Additions
Add to run artifacts + UI summary:
1. `triage_recommendation_generated_total`
2. `triage_recommendation_reused_total`
3. `triage_recommendation_fresh_total`
4. `triage_recommendation_suppressed_total`
5. `triage_recommendation_reuse_reason` (`fingerprint_match`, `fingerprint_mismatch`, `reuse_disabled`, `auto_disabled`)
6. `triage_recommendation_fingerprint`

Add per-field lanes:
1. skills fresh/reused/suppressed
2. domain fresh/reused/suppressed
3. role_family fresh/reused/suppressed

## UI Changes
In settings:
1. Toggle: `Auto Triage Recommendation` (default on)
2. Toggle: `Reuse Triage Recommendation` (default on)
3. Helper copy:
   - Auto off: "Skip recommendation generation."
   - Reuse off: "Always recompute recommendations."

In run detail:
1. Show recommendation mode badge:
   - `auto_off`
   - `fresh_only`
   - `reuse_smart`
2. Show reuse/fresh counters and mismatch reasons.

## Acceptance Criteria
1. Two toggles exist and persist correctly.
2. Auto off always results in no recommendation generation/reuse.
3. Reuse on only reuses when fingerprints match.
4. Reuse off always recomputes when auto is on.
5. Overlay replacement invalidates incompatible reuse on next run/recompute.
6. Artifacts/UI expose fresh vs reused counts and reasons.

## Test Plan

### Unit tests
1. behavior matrix resolution from (auto, reuse) settings.
2. fingerprint compatibility evaluator.
3. invalidation reason mapping.

### Route/integration tests
1. auto off: no recommendation payload generated.
2. auto on + reuse off: recommendations regenerated.
3. auto on + reuse on + matching fingerprint: reused path observed.
4. auto on + reuse on + mismatched fingerprint: fresh path observed with reason.
5. per-field counters populated for skill/domain/role_family lanes.

## Rollout Strategy
1. Phase 1: add settings + observability fields.
2. Phase 2: enforce fingerprint-gated smart reuse.
3. Phase 3: polish run-detail/operator diagnostics.

## Risks
1. Fingerprint too coarse -> accidental stale reuse.
2. Fingerprint too strict -> low reuse rate, more cost.
3. Missing observability -> hard to debug reuse decisions.

## Done Criteria
1. Operators can independently control generation and reuse.
2. Default path is safe and efficient (`auto=true`, `reuse=true` with smart gating).
3. Reuse decisions are transparent in artifacts and UI.
