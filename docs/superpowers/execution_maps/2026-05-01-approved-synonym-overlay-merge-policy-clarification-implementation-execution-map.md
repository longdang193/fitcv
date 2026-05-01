---
layer: change
artifact_type: implementation_execution_map
status: proposed
source_spec:
  - docs/superpowers/specs/2026-05-01-approved-synonym-overlay-merge-policy-clarification-spec.md
parent_thread: workstream-agentic-synonym-management.agentic-synonym-review-queue-and-approval
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - docs/api.md
  - docs/usage.md
  - docs/observability.md
  - tests/test_fitcv_cp/test_app.py
---

# Approved Synonym Overlay Merge Policy Clarification — Implementation Execution Map

## Execution Goal

Implement and verify a single, explicit contract:

- approved synonym export is delta-only (run-approved rows only)
- promote-to-global is merge/overlay (never blind replacement)
- preview/summary surfaces clearly show new/unchanged/override outcomes

## Wave 1 — Backend Contract Hardening

## Scope

- audit and harden approved export path
- harden promote preview classification behavior
- harden promote commit merge behavior and counters

## Tasks

1. Verify `approved-synonym-proposals.yaml` generation reads only run-scoped approved proposals.
2. Ensure preview classification is explicit for:
   - `new_alias`
   - `unchanged_alias`
   - `override_alias`
3. Ensure promote commit merges selected deltas into base map and preserves unrelated base entries.
4. Ensure promote summary returns/redirects include counts:
   - `applied`
   - `skipped`
   - `failed`
   - `new_aliases`
   - `unchanged_aliases`
   - `overridden_aliases`

## Exit Criteria

- Backend surfaces return deterministic classification and merge behavior consistent with the spec.

## Wave 2 — UI Clarification

## Scope

- tighten operator wording in run detail and promote preview
- remove ambiguity about replacement behavior
- improve promote selection ergonomics

## Tasks

1. Update synonym review helper text to state:
   - export is run-approved delta only
   - promote is merge/overlay onto global canonical map
2. Add `Select All` for eligible promote rows in run detail.
3. Show selected-count feedback near promote action controls.
4. Keep per-row deselect available after `Select All`.
5. Update promote preview section labels for classification buckets.
6. Ensure the summary banner reflects new/unchanged/override outcomes.

## Exit Criteria

- UI copy no longer suggests full file replacement behavior.

## Wave 3 — Docs Alignment

## Scope

- align root docs and API docs with runtime contract

## Tasks

1. Update `docs/api.md` endpoint behavior for:
   - approved export
   - promote preview
   - promote commit
2. Update `docs/usage.md` operator flow text.
3. Update `docs/observability.md` promote summary/audit notes.

## Exit Criteria

- docs reflect the same merge/overlay contract used by code/UI.

## Wave 4 — Verification And Regression Tests

## Scope

- test-level proof for export/preview/commit semantics

## Tasks

1. Add/extend tests in `tests/test_fitcv_cp/test_app.py` for:
   - delta-only export
   - preview classification (`new`, `unchanged`, `override`)
   - commit preserves unrelated base synonyms
   - commit overrides only selected colliding aliases
   - `Select All` marks only eligible approved rows
   - selected-count reflects select/deselect transitions
2. Run targeted app tests for synonym proposal flows.
3. Run repo validator fast path.

## Exit Criteria

- tests pass and validator checks complete with no new hard failures from this change.

## Verification Commands

```powershell
python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym and (promote or overlay or export or review)"
python scripts/validate_repo_contracts.py --fast
```

## Risks And Guardrails

- Risk: accidental full replacement semantics in promote commit.
  - Guardrail: explicit merge tests preserving unrelated base keys.
- Risk: ambiguous operator mental model remains.
  - Guardrail: UI + docs wording updates in same patch set.
- Risk: count drift between preview and commit summaries.
  - Guardrail: shared classification helper + test assertions.

## Definition Of Done

1. Contract implemented in backend, UI, and docs.
2. Promote behavior proven merge/overlay, not replacement.
3. Export behavior proven delta-only.
4. Tests and validator run outputs confirm no regression.
