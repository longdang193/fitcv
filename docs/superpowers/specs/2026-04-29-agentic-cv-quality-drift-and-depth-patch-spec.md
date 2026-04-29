---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-cross-seam-calibration
targets:
  - docs/intent/workstreams/threads/workstream-bounded-agentic-cv-quality/04-agentic-cv-quality-cross-seam-calibration.md
  - src/fitcv/cv_generator.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/templates/run_detail.html
  - docs/configuration.md
  - docs/observability.md
  - tests/test_cv_generator.py
  - tests/test_agentic_cv_generation.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - cv_system
  - settings_system
  - inspection_debugging
related_stages:
  - cv_analysis
  - cv_generation
---

# Agentic CV Quality Drift And Depth Patch

## Summary

Patch the highest-impact CV quality regressions in the agentic path first:

1. close operator-visible drift between settings intent and actual live-generation runtime
2. fix project rendering that collapses project detail into date/time-only text
3. add bounded depth guardrails so experience and projects are not structurally shallow when evidence exists

This is a patch-first quality recovery slice, not a full generation redesign.

## Problem

Recent runs show accepted CVs with low practical quality:

- `Projects` section sometimes renders only date range context while dropping useful bullets
- `Experience` sections can be too shallow even when selected evidence includes richer content
- operators cannot quickly tell whether current settings align with the actual runtime model/provider used by agentic generation

This creates confusion:

- users infer upstream analysis is broken when the issue is often generation/render behavior
- settings changes appear ineffective when runtime provenance diverges

## Goals

- ensure project markdown includes substantive project bullet content when available
- enforce minimum bounded depth for experience/project content in agentic generation outputs
- surface settings-vs-runtime drift clearly in run inspection surfaces
- keep changes bounded and backward-compatible with current artifact contracts

## Non-Goals

- no full prompt-contract rewrite
- no expansion into raw transcript persistence
- no replacement of existing validation framework
- no attempt to solve all stylistic CV quality concerns in one patch

## Patch Scope

## 1) Project Rendering Integrity (Immediate)

`src/fitcv/cv_generator.py`

Contract:

- when a project has both `context` and `bullets`, markdown output must include both
- `context` remains as compact metadata (for example date range)
- bullet lines remain the substantive project content

Acceptance:

- rendered markdown `## Projects` section must not collapse to context-only when bullets exist
- tests prove project output includes at least one bullet for projects with bullet data

## 2) Agentic Depth Guardrails (Bounded)

`src/fitcv/agentic_cv_generation.py`

Add a bounded post-generation quality guard before accept:

- if `experience` entries exist, each entry should contain at least one non-empty bullet
- for accepted outputs with projects present, a project with only date-range-like context and no bullets is treated as shallow
- when shallow structure is detected and repair budget remains, run one bounded repair attempt with explicit missing-depth instruction

Behavior:

- this is not open-ended rewriting; max one additional bounded repair step
- if repair still fails depth checks, keep deterministic outcome (`validation_failed` or bounded failure path) with reason fields

Acceptance:

- regression test covers shallow project/context-only output and verifies repair attempt is triggered
- regression test covers shallow experience bullets and verifies non-accept without bounded repair attempt

## 3) Settings vs Runtime Drift Surface

`src/fitcv_cp/templates/run_detail.html` (+ supporting app payload fields)

Add a compact drift indicator in run detail for agentic generation:

- expected source: effective settings snapshot for the run
- actual source: runtime provenance from `cv_generation` debug/trace records
- compare at least provider and model identity

Statuses:

- `aligned`
- `drifted`
- `not_applicable` (non-agentic or no attempted generation)

Rules:

- do not expose secrets
- keep this as operator diagnostics, not editable controls

Acceptance:

- run detail shows alignment state for agentic runs
- tests cover aligned and drifted sample payloads

## 4) Settings Surface Clarification

`src/fitcv_cp/settings_schema.py` + `settings.html` copy

Clarify that provider glue/runtime env controls are setup-managed and not on-page editable:

- settings page text must explicitly distinguish:
  - operator-tunable future-run defaults
  - setup/runtime provider configuration (for example env-managed provider/model bridge)

Acceptance:

- no new secret/provider credential controls added to settings page
- tests verify expected copy and absence of forbidden editable controls

## Observability And Evidence

Patch verification should use existing artifacts:

- `cv-debug.json`
- `cv_generation.json`
- `agentic-live-trace.json`

New/updated reason fields should clearly indicate shallow-output repair triggers and outcomes.

## Validation Plan

Minimum checks:

```powershell
python -m pytest tests/test_cv_generator.py -k render_cv_markdown
python -m pytest tests/test_agentic_cv_generation.py -k "shallow or repair or projects or experience"
python -m pytest tests/test_fitcv_cp/test_app.py -k "run_detail or settings"
python scripts/validate_repo_contracts.py --fast
```

Manual run check:

- execute one agentic run with known project bullets in candidate profile
- verify generated markdown projects section includes both context and bullet content
- verify run detail drift badge reflects actual provenance vs settings expectation

## Risks

- overly strict depth checks could reduce accept rate if not bounded carefully
- repair prompts that are too generic may increase latency without quality gain
- drift badge may be noisy if comparison fields are not normalized

## Rollout

Order:

1. land rendering fix and tests
2. land bounded depth guardrails + tests
3. land run-detail drift indicator
4. land settings-page clarification copy

Rollback:

- each slice can be reverted independently; rendering fix is lowest-risk and should remain even if later slices are rolled back

## Next Artifact

Implementation plan with bounded waves:

1. renderer correctness wave
2. generation-depth guardrail wave
3. operator drift-surface wave
4. docs + validator pass
