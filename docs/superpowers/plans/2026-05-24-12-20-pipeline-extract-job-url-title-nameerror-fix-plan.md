---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: Fix pipeline stage-transition NameError for job URL/title extractors
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-05-24-12-15-pipeline-extract-job-url-title-nameerror-fix-spec.md
targets:
  - src/fitcv/pipeline.py
related_features: []
related_stages: []
---

# Implementation Plan: Fix `_extract_job_url` / `_extract_job_title` NameError in pipeline stage-transition artifacts

## Goal

Restore live-run pipeline stability by removing invalid references to deleted/renamed private symbols in `src/fitcv/pipeline.py` stage-transition artifact wiring.

## Key Deliverables

- Stage-transition artifacts builder does not raise `NameError` for job URL/title extraction.
- Targeted tests covering stage-transition artifacts pass.
- Live run (Docker compose) can reach `status=succeeded` for `/runs` trigger.

## Task/Wave Breakdown

### Task 0: Reproduce + capture evidence

- [x] Reproduce live run failure via Docker compose + `/runs` trigger.
- [x] Capture failure boundary:
  - `error_message`: `name '_extract_job_url' is not defined`
  - worker stacktrace points to `src/fitcv/pipeline.py` stage-transition artifact build path.

### Task 1: Root cause investigation

- [x] Confirm `_extract_job_url` and `_extract_job_title` are referenced but not defined in `src/fitcv/pipeline.py`.
- [x] Confirm canonical extractors already exist and are imported:
  - `extract_job_url`, `extract_job_title` from `fitcv.pipeline_stages.common`.

### Task 2: Minimal fix

- [x] Replace invalid wiring:
  - `extract_job_url=_extract_job_url` -> `extract_job_url=extract_job_url`
  - `extract_job_title=_extract_job_title` -> `extract_job_title=extract_job_title`

### Task 3: Verification

- [x] Tests: `uv run pytest tests/test_pipeline.py -k "stage_transition_artifacts"` (PASS; 13 tests).
- [x] Repo validator: `python scripts/hooks/run_validator.py --fast` (PASS).
- [x] Live run smoke (Docker compose):
  - `GET /healthz` 200
  - `POST /runs` 201 and polled to terminal `status=succeeded`

## Completion Criteria

- [x] Deliverables satisfied.
- [x] No unresolved checklist items remain in this plan.

## Verification

- [x] `uv run pytest tests/test_pipeline.py -k "stage_transition_artifacts"` (PASS; 13 tests)
- [x] `python scripts/hooks/run_validator.py --fast` (PASS)
- [x] Live run smoke (Docker compose) reached terminal `status=succeeded`
