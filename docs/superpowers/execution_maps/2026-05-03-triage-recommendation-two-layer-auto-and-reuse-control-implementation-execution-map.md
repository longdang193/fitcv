---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: workstream-agentic-synonym-management
map_type: implementation_execution
threads:
  - workstream-agentic-synonym-management.agentic-synonym-proposal-engine
specs:
  - docs/superpowers/specs/2026-05-03-triage-recommendation-two-layer-auto-and-reuse-control-spec.md
---

# 2026-05-03 Triage Recommendation Two-Layer Auto + Reuse Control Implementation Execution Map

Spec reference:
- `docs/superpowers/specs/2026-05-03-triage-recommendation-two-layer-auto-and-reuse-control-spec.md`

## Objective
Implement clean two-layer triage recommendation controls:
1. auto generation toggle,
2. reuse toggle with smart fingerprint gating.

## Wave 1: Settings + Runtime Mode
1. Add settings keys in schema:
   - `synonym_management.auto_triage_recommendation_enabled` (default true)
   - `synonym_management.triage_recommendation_reuse_enabled` (default true)
2. Extend `_synonym_management_mode()` to expose these booleans.
3. Ensure run-detail context carries this mode for diagnostics.

## Wave 2: Triage Refresh Contract
1. Apply behavior matrix in `/synonym-proposals/triage-refresh`:
   - auto off: skip generation/reuse; record `auto_disabled`.
   - auto on + reuse off: force fresh generation.
   - auto on + reuse on: reuse only on fingerprint match, else fresh generation.
2. Extend triage fingerprint to include compatibility guard inputs:
   - proposal payload,
   - runtime policy/version,
   - run overlay fingerprint.
3. Record trace summary counters and reasons.

## Wave 3: Observability
1. Persist triage summary in `synonym_proposals_trace.trace_summary`:
   - generated/reused/fresh/suppressed totals
   - reuse reason fields
2. Surface mode badge + counters in run detail queue model.

## Wave 4: Tests
1. Update triage-refresh route tests for new query fields and behavior.
2. Add tests:
   - auto disabled path,
   - reuse disabled fresh-only path,
   - reuse enabled + fingerprint match path,
   - reuse enabled + mismatch path.

## Exit Criteria
1. Two toggles control behavior exactly as defined by matrix.
2. Reuse is fingerprint-safe and invalidates on overlay/policy drift.
3. Route tests pass with explicit observability signals.
