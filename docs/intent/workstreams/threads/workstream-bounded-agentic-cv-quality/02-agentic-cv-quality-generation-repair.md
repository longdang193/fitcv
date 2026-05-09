---
thread_id: workstream-bounded-agentic-cv-quality.agentic-cv-quality-generation-repair
status: completed
parent_spec: docs/superpowers/specs/2026-04-29-agentic-cv-quality-drift-and-depth-patch-spec.md
implementation_plan: docs/superpowers/plans/2026-04-28-fitcv-wave-3-input-analysis-parity-grounding-plan.md
---
# agentic-cv-quality-generation-repair

## Goal

Improve rewrite, repair, and validator-recovery behavior in cv_generation.

## Why Now

Better repair loops improve accepted outputs without relaxing validation.

## Dependencies

analysis grounding signals

## Shared Surfaces

src/fitcv/agentic_cv_generation.py; validator bridge

## Linked Spec

- none yet

## Linked Plan

- none yet

## Notes

Keep deterministic validation final.

