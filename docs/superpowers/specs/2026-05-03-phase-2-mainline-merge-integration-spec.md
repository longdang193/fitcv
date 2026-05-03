---
layer: operating_system
artifact_type: spec
status: active
parent_workstream: workstream-fitcv-semantic-spine
targets:
  - docs/intent/
  - scripts/validate_planning_lifecycle.py
  - scripts/validate_checkpoint_packs.py
  - scripts/validate_repo_contracts.py
  - src/fitcv/
  - src/fitcv_cp/
  - tests/
related_features: []
related_stages: []
---

# Phase 2 Mainline Merge Integration Spec

## Triage

Layer: operating_system  
Feature type: UPDATE  
Summary: Merge `origin/main` into `codex/observability-evidence-phase2` without losing Phase 2 closeout work, and with deterministic conflict resolution plus validation gates.  
Reasoning: The branch is materially ahead on Phase 2 execution while `main` has newer baseline changes. We need integration without changing `main`, while preserving lifecycle evidence and runtime behavior.  
Invariants:

- `main` remains unchanged; integration happens only in branch history
- no Phase 2 closeout artifacts are dropped during conflict resolution
- merged branch must pass lifecycle and checkpoint validators
- merge must be recoverable via pre-merge checkpoint commit

Dependencies:

- `origin/main`
- `codex/observability-evidence-phase2`
- local Phase 2 docs, runtime code, and tests already authored in branch

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

Current branch has local and committed Phase 2 changes, while `origin/main` has additional updates.
Running merge in a dirty working tree risks mixed edits, ambiguous conflict outcomes, and loss of evidence integrity.

## Goal

Define a safe, repeatable merge procedure to integrate `origin/main` into Phase 2 branch while preserving branch-specific closeout work and guaranteeing validation pass before continuation.

## Non-Goals

- rewriting or rebasing `main`
- force-pushing `main`
- broad rescoping of Phase 2 intent
- changing workstream lifecycle statuses as part of merge mechanics alone

## Merge Contract

### 1. Pre-Merge Hygiene

- working tree must be clean before merge command
- if local changes exist, create checkpoint commit (preferred) or stash
- record current head SHA for rollback reference

### 2. Merge Operation

- fetch latest refs
- merge `origin/main` into current branch (no rebase requirement in this pass)
- resolve conflicts with branch-preservation bias for Phase 2 closeout artifacts:
  - preserve branch-intended lifecycle/checkpoint state
  - incorporate upstream baseline improvements where non-conflicting

### 3. Conflict Resolution Policy

Prioritize correctness in this order:

1. lifecycle integrity and checkpoint evidence consistency
2. runtime behavior correctness and tests
3. docs/generated artifacts refresh for consistency

When conflicts involve both lifecycle metadata and code:

- resolve metadata first (to avoid invalid status/evidence drift)
- resolve code second
- regenerate derived docs/artifacts if required

### 4. Required Validation Gate (Post-Merge)

```powershell
python scripts/validate_planning_lifecycle.py --strict
python scripts/validate_checkpoint_packs.py
python scripts/validate_repo_contracts.py --fast
```

If targeted runtime files are conflicted/resolved, also run:

```powershell
pytest tests/test_pipeline.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py
```

Merge integration is not complete until all required commands pass.

## Deliverables

- merged branch containing `origin/main` updates
- preserved Phase 2 closeout artifacts and statuses
- passing lifecycle/checkpoint/repo-contract validators
- checkpoint note documenting merge resolution decisions

## Acceptance Criteria

- branch contains merge commit from `origin/main`
- `main` branch remains untouched
- no missing checkpoint packs for completed threads
- strict lifecycle validation passes
- fast repo contract validation passes

## Risks and Mitigations

- Risk: accidental overwrite of Phase 2 lifecycle evidence  
Mitigation: conflict policy explicitly favors lifecycle correctness plus immediate validator run.

- Risk: hidden regressions in runtime merge hotspots  
Mitigation: run targeted tests for pipeline/control-plane files touched by conflicts.

- Risk: unresolved local untracked files pollute merge context  
Mitigation: pre-merge hygiene checkpoint and explicit clean-tree requirement.

## Rollout

Phase 1:

- create pre-merge checkpoint commit
- perform merge and resolve conflicts

Phase 2:

- run mandatory validators and targeted tests
- document merge checkpoint evidence

Phase 3:

- continue Phase 2 execution on updated branch baseline
