---
name: skill-subagent-driven-development
description: Use when an approved plan needs sequential fresh subagents under validated harness packets.
required_reads: []
distribution_tier: starter_kit
---
# Subagent-Driven Development

Use only when controller selects `sequential_work_lanes` in a managed harness run
and host adapter capability is `enforced`. `skill-executing-plans` owns
ordinary direct execution.

## Controller Contract

- Controller classifies request, selects only `low`, `normal`, or `high`, and
  starts managed run through host-supplied `run_managed` adapter boundary.
- Run record owns immutable attempt packet, lanes, claims, change-set evidence,
  friction, outcomes, decisions, and state history under `.harness/runs/`.
- Packet owns allowed paths, planned write paths, resolved base commit,
  workspace, tools, checks, approval gates, required rules, and orchestration
  mode.
- For active plan-linked coordination, manifest owns static task dependencies,
  topology, and planned paths. Packet owns immutable `plan_ref`, task ID, and
  digest; `run.json` owns state and handoff. Controller selects only `ready`
  task through `coordination-status`; changed plan or base requires successor.
- One implementer lane runs at once in an adapter-owned isolated workspace. No child-agent spawning.
- Implementer returns `claimed_result`, never `verified`.
- Harness records outcome after dispatch, claim collection, and verification.
  Controller alone calls `apply_controller_decision` to accept, retry,
  escalate, request approval, or block. Commit policy remains separate.
- Generic CLI has no platform agent adapter. It must return
  `execution_mode_unavailable`, not claim dispatch occurred.
- Controller may record `waive` only with reason. Waived work is terminal
  `unvalidated`; local proof remains local and cannot become managed acceptance.
- Independent validator evidence requires host dispatch of a separate enforced,
  read-only validator lane. Implementer claims and local checks do not count.

## Per Task

1. Controller builds version-3 request with typed criteria. For plan-linked
   work it sends `plan_ref` and `plan_task_id` only; core derives mode, base,
   and planned paths before enforced host dispatch.
2. Harness authorizes planned protected paths, prepares workspace, dispatches,
   collects claim, snapshots actual changes, and records criterion evidence.
3. Implementer changes only lane paths, runs task-local proof, and reports
   claim, changed files, concerns, and normalized friction.
4. If review is required, controller obtains read-only reviewer evidence. Review
   cannot authorize protected paths; approval cannot prove semantic criteria.
5. Controller records one allowed decision. Retry, escalation, and approval
   resume create successor attempts; prior packets and evidence stay unchanged.

## Stop

Stop with managed `block` when host capability is unavailable, lane scope
overlaps another active writer, proof cannot run, or approval gate triggers.
Use explicit `waive` only to record local-only `unvalidated` work. Do not use
manual controller glue to bypass recorded outcome or decision.

For managed terminal failure, return packet evidence only. Core records
friction; controller alone routes recurring candidates to `skill-improve-harness`.
