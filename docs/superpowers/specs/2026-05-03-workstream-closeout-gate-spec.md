---
layer: operating_system
artifact_type: spec
status: completed
parent_workstream: none
targets:
  - docs/intent/workstreams/
  - docs/intent/workstreams/threads/
  - docs/intent/workstreams/checkpoints/
  - docs/operating_system/prompt_templates/workstream-completion-and-intent-check-prompt.md
  - scripts/validate_planning_lifecycle.py
  - scripts/validate_checkpoint_packs.py
  - scripts/validate_repo_contracts.py
related_features: []
related_stages: []
---

# Workstream Closeout Gate Spec

## Triage

Layer: operating_system  
Feature type: ADD  
Summary: Add a mandatory closeout gate that blocks marking a plan bundle or workstream as complete unless thread statuses and checkpoint evidence are reconciled.  
Reasoning: Recent execution showed a hygiene gap where implementation completion was recorded, but workstream/thread metadata remained stale (`active`/`proposed`). This creates false progress signals and weakens lineage trust.  
Invariants:

- completion claims must match lineage metadata state
- completed workstreams must not contain non-terminal thread statuses
- closed threads must have checkpoint evidence
- validators must catch status/evidence drift before merge or push

Dependencies:

- `docs/intent/workstreams/*.md`
- `docs/intent/workstreams/threads/**/*.md`
- `docs/intent/workstreams/checkpoints/**`
- `scripts/validate_planning_lifecycle.py`
- `scripts/validate_checkpoint_packs.py`
- `scripts/validate_repo_contracts.py`

Affected stages:

- none

Affected features:

- none

Primary lens: cross-cutting

Generated refresh required: yes
Capability IDs: none
Invariant IDs: none
Spec needed: yes
Plan needed: yes

## Problem

The current process allows this failure mode:

1. plan bundle marked `completed`
2. workstream and/or thread statuses not reconciled
3. some threads remain `proposed`/`active`
4. repo presents inconsistent completion state

This is a metadata/status hygiene failure, not always missing code execution.

## Goal

Define and enforce a closeout gate that guarantees status and evidence reconciliation whenever closure is claimed.

## Non-Goals

- redesigning the entire planning ladder
- replacing existing roadmap/workstream/thread structures
- forcing artificial implementation where intentional scope drop is valid

## Closeout Gate Contract

### 1. Trigger

Run the gate whenever either occurs:

- a plan bundle is set to `status: completed`
- a workstream is set to `status: completed`

### 2. Required Reconciliation

For the target workstream:

- every thread must be terminal:
  - allowed: `completed`, `dropped`
  - disallowed: `proposed`, `active`, `blocked` (unless workstream remains non-completed)
- each terminal thread must have checkpoint evidence:
  - at least one checkpoint result pack in
    `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- if thread is `dropped`, closeout note must explain why and what replaced/deferred it

### 3. Validation Commands

Mandatory commands before closeout:

```powershell
python scripts/validate_planning_lifecycle.py --strict
python scripts/validate_checkpoint_packs.py
python scripts/validate_repo_contracts.py --fast
```

Closeout is invalid if any command fails.

### 4. Prompt Ritual

Before final closeout, run:

- `workstream-completion-and-intent-check-prompt.md`

Expected output must include:

- completion verdict (`complete | partial | not_complete`)
- done/missing/drifted breakdown
- explicit thread-status reconciliation decisions
- next decision (`close | continue | re-scope`)

## Data/Schema Requirements

### Workstream

- when `status: completed`, no non-terminal child thread statuses are allowed

### Threads

- canonical statuses:
  - `proposed`, `active`, `blocked`, `completed`, `dropped`
- terminal statuses for completed workstream:
  - `completed`, `dropped`

### Checkpoint Packs

- must follow canonical section shape:
  - `## Intent`
  - `## Actions`
  - `## Visible Output`
  - `## Status`
  - `## Next Decision`

## Implementation Plan (High Level)

1. Validator hardening
- extend lifecycle validator to enforce terminal-only threads for completed workstreams (already introduced in starter)
- extend/confirm checkpoint validator coverage for terminal threads

2. Prompt/process hardening
- update execute/closeout prompt guidance to explicitly require reconciliation step
- add checklist entry to plan-completion workflow

3. CI/hook enforcement
- keep lifecycle validation in `validate_repo_contracts.py --fast`
- adopt `--strict` in CI for repos that want hard gating on warning-class coverage drift

## Acceptance Criteria

- cannot mark workstream complete while any child thread is `proposed` or `active`
- cannot complete thread without required checkpoint evidence
- closeout commands fail on mismatch
- closeout prompt output explicitly captures status reconciliation
- no stale “active/proposed” threads remain after accepted closeout

## Risks And Mitigations

- Risk: teams bypass gate for urgent merges  
Mitigation: enforce in CI and protected branch checks.

- Risk: false failures on legacy data  
Mitigation: initial migration mode with targeted backlog cleanup, then strict enforcement.

## Rollout

Phase 1 (advisory):

- run gate commands and report failures without blocking

Phase 2 (enforced):

- require gate pass for merge/push on protected branches

Phase 3 (steady state):

- strict closeout required for all completed plan bundles and workstreams
