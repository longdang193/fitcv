---
thread_id: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
status: active
---

# operator-control-plane-agentic-settings-surface

## Goal

Add a bounded operator-facing settings surface for real agentic runtime controls.

## Why Now

The settings page now aligns better with runtime truth, but it still has no
explicit operator-owned section for supported agentic controls.

## Dependencies

settings system contract; agentic observability contract; bounded agentic CV
quality seams; deterministic late-stage truth

## Shared Surfaces

settings UI; settings schema; run-scoped settings-used snapshots; agentic
inspection surfaces

## Linked Spec

- docs/superpowers/specs/2026-04-28-operator-control-plane-agentic-settings-surface-spec.md

## Linked Plan

- docs/superpowers/plans/2026-04-28-operator-control-plane-agentic-settings-surface-plan.md

## Notes

Expose only real operator-tunable agentic controls. Do not surface agentic
internals, hidden provider glue, or settings that belong only in setup or
deployment.

The first bounded implementation centers the new `/admin/settings` `Agentic`
section on late-stage agentic enablement plus semantic-alignment defaults,
while leaving run-history truth in run detail and `settings-used.json`.
