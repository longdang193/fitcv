---
thread_id: workstream-operator-control-plane.operator-control-plane-run-detail-truth
status: active
---

# operator-control-plane-run-detail-truth

## Goal

Keep runs list, run detail, stage progress, and lifecycle actions truthful to runtime state.

## Why Now

Run detail is the operator ground truth surface.

## Dependencies

semantic-spine-stage-authority-contract

## Shared Surfaces

src/fitcv_cp/app.py; templates; run events

## Linked Spec

- docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md

## Linked Plan

- docs/superpowers/plans/2026-05-03-operator-control-plane-run-detail-truth-bootstrap-plan.md

## Notes

Outcome truth wins over convenience copy.

