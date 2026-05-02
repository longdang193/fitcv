---
workstream_id: workstream-operator-control-plane
status: active
---

# Workstream: Operator Control Plane

## Purpose

Preserve and strengthen the original FitCV control-plane experience so operators can run, pause, continue, inspect, and export without terminal-first workflows.

## Owns

- trigger inputs and execution-mode selection
- runs list and run detail as the authoritative operator surfaces
- checkpoint continuation and lifecycle actions
- stage progress, status truth, and download paths
- settings and controls that match real runtime ownership

## Does Not Own

- acceptance semantics themselves
- agentic reasoning quality
- repo-method or agent tooling concerns

## Dependencies

- `admin_control_plane_core`
- `trigger_run_management`
- `inspection_debugging`
- `settings_system`

## Key Risks

- UI drift away from the original control-plane shape
- exposing stage states that do not reflect real runtime truth
- adding convenience surfaces that hide authoritative outcomes

## Phase 2 Alignment

In Master Workstream Phase 2, this workstream is the source of truth for:

- operations = control plane UI

It should surface degraded-evidence state clearly, preserve recommendation-vs-acceptance clarity, and keep replay/approval actions aligned with policy ownership rather than UI convenience.
