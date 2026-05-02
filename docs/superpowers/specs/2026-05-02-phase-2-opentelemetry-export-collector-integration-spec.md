---
layer: workstream
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-otel-export-and-collector-integration
---

# 2026-05-02 Phase 2 OpenTelemetry Export Collector Integration Spec

## Summary

Implement OpenTelemetry export and collector integration for runtime telemetry transport while retaining stage artifacts as authoritative evidence.

## Scope

- OTel SDK wiring and context propagation
- exporter and collector configuration
- operator-visible degradation signaling for export failures

## Non-Goals

- replacing stage artifact evidence with telemetry backend data
- full ClickHouse/MLflow rollout

## Acceptance

1. OTel export path is operational and configurable.
2. Trace context continuity remains stable across artifacts/events/export.
3. Export failure behavior is non-destructive and operator-visible.
