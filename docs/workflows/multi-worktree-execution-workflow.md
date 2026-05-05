---
workflow_id: multi-worktree-execution
type: workflow
stage: execution
owner_layer: change
entry_points:
  - multiple independent bugfix or feature lanes should run in parallel
  - a single lane is blocked and decomposition into isolated worktrees is required
prerequisites:
  - in-scope roadmap/workstream/thread and plan/spec context is identified
  - lane boundaries and ownership can be defined without uncontrolled overlap
next_steps:
  - multi-worktree-dispatch-prompt.md
  - implementation-next-action-gate-prompt.md
  - thread-closeout-readiness-prompt.md
skills:
  - using-git-worktrees
  - dispatching-parallel-agents
  - executing-plans
  - verification-before-completion
status: active
outputs:
  - lane registry with owner, worktree path, and current status
  - per-lane verification evidence and closeout readiness state
validators:
  - each lane has bounded scope and explicit next action
  - each lane has verification evidence before completion claims
---

# Multi-Worktree Execution Workflow

## Goal

Execute multiple independent development lanes safely using isolated worktrees,
bounded scope, and explicit merge/closeout controls.

## Execution Flow

1. Run routing gate and decide whether lane splitting is warranted.
2. Define lane registry:
   - lane id
   - owner
   - objective
   - expected files/modules
   - verification commands
3. Create one worktree per lane with clean baseline checks.
4. Execute each lane with bounded changes only.
5. Apply patch-pattern detection for patch-heavy lanes.
6. Verify each lane before merge claims.
7. Merge in dependency-safe order and rerun shared regression checks.
8. Reconcile lifecycle/status evidence and close out.

## Decision Gates

1. Decomposition gate:
   - split lanes only when scope boundaries are independent enough.
2. Overlap gate:
   - if two lanes require the same hot files, re-slice before execution.
3. Evidence gate:
   - no lane can claim complete without fresh verification evidence.
4. Merge gate:
   - merge only lanes that satisfy bounded scope + validation requirements.
5. Closeout gate:
   - run thread/workstream closeout prompts when lifecycle states change.

## Partial Entry Rules

- If worktrees already exist, enter at lane execution/verification.
- If a lane already failed, enter at lane debugging and bounded rerun.
- If implementation is done but closure is pending, enter at lifecycle reconciliation.

## Exit Criteria

- All active lanes are terminal (merged or explicitly deferred).
- Evidence and status updates are reconciled.
- Next action is explicitly selected if any lane remains open.

