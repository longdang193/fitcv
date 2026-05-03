---
thread_id: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
status: completed
---

# operator-control-plane-phase-2-degraded-mode-and-portability-surface

## Goal

Define Phase 2 operator-facing control semantics for portability:

- operations = control plane UI

including clear degraded/local/full mode visibility and recommendation-vs-acceptance separation.

## Why Now

Local-database and backend-decoupling goals require clear operator truth messaging before implementation planning starts.

## Dependencies

run-detail truth thread; settings-surface alignment thread; agentic settings surface thread

## Shared Surfaces

run detail; settings-used narrative; lifecycle/replay/approval messaging

## Notes

This thread does not change acceptance authority. It clarifies how authority and degraded evidence state are shown to operators.
