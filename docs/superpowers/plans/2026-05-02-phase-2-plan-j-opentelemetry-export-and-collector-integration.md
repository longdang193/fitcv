---
layer: workstream
artifact_type: plan
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-otel-export-and-collector-integration
parent_spec: docs/superpowers/specs/2026-05-02-phase-2-opentelemetry-export-collector-integration-spec.md
targets:
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv/pipeline.py
  - config
  - tests/test_fitcv_cp/test_app.py
  - tests/test_pipeline.py
  - docs/observability.md
  - docs/architecture.md
related_features:
  - inspection_debugging
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

# Phase 2 Plan J OpenTelemetry Export And Collector Integration

**Goal:** Implement standard OpenTelemetry emission/export so existing OTel-compatible trace context is transported to a telemetry backend.

## Scope

- instrument telemetry emit path with OpenTelemetry spans/events
- propagate `trace_id`/`span_id`/parent context across stage and event boundaries
- wire exporter/collector configuration with safe runtime fallback behavior
- expose operator-visible degradation signals when telemetry export fails

## Non-Goals

- replacing stage-owned evidence artifacts with telemetry backend
- full backend migration to ClickHouse/MLflow in this plan
- policy decision logic changes

## Execution-Pass Checkpoint Requirement

Each bounded-thread execution pass in this plan must publish one checkpoint result pack.

Required:

- create/update one pack per meaningful execution pass
- store pack at `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- follow `docs/operating_system/templates/checkpoint-result-pack.md`
- mark status as `pass`, `partial`, or `fail`
- include intent, actions, visible output, and next decision

## Tasks

## Task 1: OTel Runtime Wiring
- [ ] Add OpenTelemetry SDK setup and context propagation hooks.
- [ ] Bind stage execution and event writes to OTel spans using canonical IDs.

## Task 2: Exporter + Collector Path
- [ ] Add configurable exporter setup (OTLP endpoint and runtime toggles).
- [ ] Provide safe fallback when exporter/collector is unavailable.

## Task 3: Control-Plane Diagnostics
- [ ] Surface telemetry export degradation in operator-visible run diagnostics.
- [ ] Keep stage artifacts as authoritative evidence regardless of telemetry backend state.

## Task 4: Tests + Docs
- [ ] Add tests for context propagation and exporter-failure behavior.
- [ ] Update observability docs with setup, fallback, and troubleshooting guidance.

## Verification

```powershell
python -m pytest tests/test_fitcv_cp/test_app.py
python -m pytest tests/test_pipeline.py
python scripts/validate_repo_contracts.py --fast
python scripts/validate_checkpoint_packs.py
```

## Exit Criteria

1. OTel export path is running and configurable.
2. Trace context continuity remains stable across artifacts and telemetry events.
3. Export failure modes are operator-visible and non-destructive.
4. Stage artifacts remain the evidence source of truth.
