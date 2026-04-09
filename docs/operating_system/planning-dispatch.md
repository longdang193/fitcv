# Planning Dispatch

This document defines the minimum planning gate for non-trivial changes.

## Purpose

Before writing a spec or plan, identify:

- what kind of change this is
- which feature or operating-system area owns it
- whether stages are affected
- which docs must move with it

## Triage Block

Use this block before specs or implementation plans:

```text
Feature type: ADD | MODIFY | REPLACE
Summary: <1 sentence>
Reasoning: <why this classification>
Invariants:
  - <must hold true>
Dependencies:
  - <if known>
Affected stages:
  - <stage_id> | none
Affected features:
  - <feature_id> | none
Primary lens: stage | feature | mixed | cross-cutting
Affected docs:
  feature_yaml: `docs/features/<feature_id>.yaml` | none
  feature_history: `docs/features/<feature_id>/history.md` | none
  feature_docs:
    - `docs/features/<feature_id>/<doc>.md`
  cross_cutting_docs:
    - `docs/<doc>.md`
    - `docs/operating_system/<doc>.md`
  readme: `README.md` | none
  generated:
    - `docs/generated/<file>`
Generated refresh required: yes | no
Spec needed: yes | no
Plan needed: yes | no
```

## Dispatch Rules

- unclear design -> write a spec first
- clear design, non-trivial execution -> write a plan
- approved plan -> implement
- cross-cutting repo workflow changes may use `Affected features: none`

## Operating-System Changes

When the change is about repo structure, publication workflow, agent instructions, or tooling policy:

- primary lens is usually `cross-cutting`
- affected features may be `none`
- the owning docs live under `docs/operating_system/`
