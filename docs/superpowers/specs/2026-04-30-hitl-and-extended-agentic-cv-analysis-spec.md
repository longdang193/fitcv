---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-review-actions
targets:
  - docs/intent/workstreams/threads/workstream-operator-control-plane/04-operator-control-plane-agentic-review-actions.md
  - docs/intent/workstreams/threads/workstream-bounded-agentic-cv-quality/01-agentic-cv-quality-analysis-grounding.md
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/worker_job.py
  - docs/observability.md
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - cv_system
  - inspection_debugging
  - trigger_run_management
related_stages:
  - cv_analysis
  - cv_generation
---

# Human-In-The-Loop Gate + Extended Agentic CV Analysis

## Summary

Add a bounded human-in-the-loop (HITL) review gate for risky late-stage CV cases
and extend agentic CV analysis outputs so generation gets stronger grounded
instructions.

This improves quality and trust without turning the pipeline into manual review
for all runs.

## Problem

Current late-stage behavior can produce acceptable-but-weak CVs in some cases:

- shallow experience/project depth despite available evidence
- uncertainty about when operator intervention is required
- analysis outputs not rich enough to drive targeted generation constraints

Operators need a clear gate for ambiguous cases and better analysis-to-generation
handoff.

## Goals

- add a bounded HITL decision gate for high-risk CV outputs
- enrich `cv_analysis` outputs with requirement-level coverage and confidence
- use enriched analysis facts to strengthen generation prompts and repair logic
- keep deterministic outcomes and run observability intact

## Non-Goals

- no open-ended manual editing surface in this slice
- no mandatory human review for all runs
- no replacement of existing validation contracts

## Proposed Contract

## 1) HITL Gate (Bounded)

Introduce a review-required status for selected late-stage records.

Trigger conditions (initial):

- low evidence coverage score for required skills
- repeated repair/depth failure
- runtime settings-vs-provenance drift
- analysis confidence below threshold

Decision actions:

- `approve` (allow persist)
- `regenerate_once` (one bounded retry)
- `reject` (mark terminal with reason)

Run behavior:

- non-HITL rows continue as today
- HITL rows pause in review-required state until operator action

## 2) Extended CV Analysis Output

Extend `cv_analysis` record contract with:

- requirement coverage table (`required_skill -> support_strength`)
- unsupported critical requirements list
- per-section drafting confidence hints (`summary`, `experience`, `projects`, `skills`)
- explicit “do not claim” list

These are compact structured fields, not raw model transcripts.

## 3) Generation Uses Analysis Hints

`agentic_cv_generation` should consume extended analysis facts:

- emphasize stronger supported requirements
- avoid unsupported claims aggressively
- enforce depth where support confidence is strong

Repair remains bounded (single extra attempt unless existing policy already
permits one).

## 4) Control Plane Review Surface

Run detail should support review actions for review-required records:

- list pending review items with reason
- action buttons: approve / regenerate once / reject
- append timeline events for each review action

## 5) Observability

Persist review metadata in run-scoped artifacts:

- review_required reason
- reviewer action
- action timestamp
- post-action outcome

Expose this in:

- run detail
- `cv-debug.json` / stage artifacts
- event timeline

## Acceptance Criteria

- reviewer can identify and resolve review-required items from run detail
- extended analysis fields are present and consumed by generation
- non-HITL rows remain fully automated
- review actions are auditable in run artifacts/events
- no secret/runtime-sensitive data is exposed through new review surfaces

## Validation

```powershell
python -m pytest tests/test_pipeline_agentic_late_stage.py -k "analysis or generation or review"
python -m pytest tests/test_fitcv_cp/test_app.py -k "run_detail or review"
python scripts/validate_repo_contracts.py --fast
```

## Risks

- too-broad trigger rules can flood operator queue
- weak thresholds can make HITL ineffective
- adding rich analysis fields without generation consumption creates dead metadata

## Next Artifact

Implementation execution map with waves:

1. analysis contract extension
2. generation consumption + bounded depth policy
3. HITL control-plane actions and statuses
4. observability/docs polish
