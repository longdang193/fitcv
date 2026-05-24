---
layer: change
artifact_type: spec
status: completed
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
targets:
  - src/fitcv/pipeline.py
related_features:
  - trigger_run_management
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Pipeline Stage-Transition Extractor NameError Fix

## Summary

Live run failed immediately with `NameError` during stage-transition artifact construction due to references to deleted/renamed private symbols `_extract_job_url` and `_extract_job_title`.

This spec defines bounded corrective change: restore wiring to canonical extractor helpers already imported from `fitcv.pipeline_stages.common`.

## Problem

When running control-plane worker, pipeline crashes:

- error: `name '_extract_job_url' is not defined`
- follow-up after partial fix: `name '_extract_job_title' is not defined`

Crash happens inside `src/fitcv/pipeline.py` while building stage transition artifacts.

## Normalization Target (SSOT)

- Use `extract_job_url` and `extract_job_title` as SSOT extractors (from `fitcv.pipeline_stages.common`).
- No stage-transition artifact builder should reference undefined `_extract_*` helpers.

## Acceptance Criteria

- Targeted tests pass:
  - `uv run pytest tests/test_pipeline.py -k "stage_transition_artifacts"`
- Live run smoke passes (Docker compose web+worker):
  - `POST /runs` run reaches terminal `status=succeeded`
- Repo contract validator passes:
  - `python scripts/hooks/run_validator.py --fast`

## Out of Scope

- Broader pipeline refactors or schema changes.
- Any change to job URL/title extraction semantics beyond swapping to SSOT helpers.
