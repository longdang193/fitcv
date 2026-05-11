---
layer: change
artifact_type: plan
status: active
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md
targets:
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv_cp/test_main.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features: []
related_stages: []
---

# SQLite E2E Backend Runtime Plan

**Feature Source:** `none`
**Feature Contract:** `none`
**Spec:** `docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md`
**Implementation Execution Map:** `none`
**Type:** modify
**Plan Layer:** change
**Plan Status:** active

## Tasks
1. Add shared backend runtime resolver for control-plane startup and worker bootstrap.
2. Refactor `fitcv_cp.main` to consume shared resolver (remove duplicated backend parsing).
3. Refactor `fitcv_cp.worker_job.execute_pipeline_run` to branch early by backend mode and skip BigQuery client in sqlite mode.
4. Add/adjust tests for sqlite worker bootstrap path and main module backend resolution integration.
5. Validate with targeted pytest and local sqlite inline e2e on `127.0.0.1:8010`.
