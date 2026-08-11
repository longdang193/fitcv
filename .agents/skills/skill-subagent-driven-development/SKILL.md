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
- For current leased packets, core issues one finite lease before `running`.
  Host owns provider process lifecycle and returns packet-declared terminal
  evidence. Core finalizes external signed and legacy evidence through
  `terminalize_attempt(envelope)`; personal-local closure uses
  `harness-core-launcher close`. Evidence records
  `attempt_outcome/v2`, one-decision terminal outcomes auto-finalize, and
  ambiguous terminal outcomes require signed controller authority. Core
  atomically records terminal evidence, receipt, lease release, state history,
  and `run.json`.
- Packet owns allowed paths, planned write paths, resolved base commit,
  workspace, tools, checks, approval gates, required rules, orchestration
  mode, and resolved `execution_budget`.
- `execution_budget.finalization_reserve_seconds` is policy-owned. Host uses
  `turn_timeout_seconds - reserve` for normal App Server work, then one
  read-only final claim turn for reserve after interruption or empty final text.
  Finalizer never writes, diagnoses, retries, resumes, or verifies work.
- For active plan-linked coordination, manifest owns static task dependencies,
  topology, allowed paths, and planned paths. Packet owns immutable `plan_ref`, task ID, and
  digest; `run.json` owns state and handoff. Controller selects only `ready`
  task through `coordination-status`; changed plan or base requires successor.
- One implementer lane runs at once in an adapter-owned isolated workspace.
  Agents may create child agents only when immutable packet grants
  `harness.delegate` and selects `read_only_research`; core enforces child
  authority, paths, depth, budget, and read-only workspace. This implementer
  packet does not select that profile, so implementer must not spawn child agents.
- Implementer returns `claimed_result`, never `verified`.
- Harness records outcome after dispatch, claim collection, and verification.
  Installed `harness-core` owns packet lifecycle. Consumer scripts only bridge
  to package commands. Controller alone selects decisions. `retry` and `escalate`
  use host-bound `harness-core-launcher decision`; commit policy remains separate.
- Generic CLI has no managed `run` command. `run-unavailable` records explicit
  `execution_mode_unavailable` proof; it never claims dispatch occurred.
- For `runtime_provider_id: codex_app_server`, controller uses active
  pointer-selected runtime through `harness-core-launcher`: run
  `harness-core-launcher doctor`, then `capabilities`, then `preflight`, then
  `run --harness-root <repo-root> --request <request.json>`. Never invoke bare
  `codex-harness-host`; PATH can resolve stale user tools. Host-owned trusted
  user configuration selects transport; do not copy endpoint, launch-command,
  or credential values into repository inputs. Use exclusive `--run-id <run-id>`
  only to resume an existing planned attempt. Do not retry through
  `run-unavailable`; preserve that terminal proof and create successor request.
- `stdio` plus `host_spawn` requires Windows containment. A preflight failure
  can carry sanitized lifecycle fields. A host `terminal_recording_failed`
  payload is recovery evidence only: preserve it for controller recovery; never
  create lane evidence, retry, or terminalize from it.
- A terminal coordinated task failure derives `blocked` status. Preserve its
  run evidence; require approved successor plan/task identity instead of a
  fresh request against same task.
- Controller may finalize controller-authorized `waive` only with reason. Waived
  work is terminal `unvalidated`; local proof remains local and cannot become
  managed acceptance.
- Independent validator evidence requires host dispatch of a separate enforced,
  read-only validator lane. Implementer claims and local checks do not count.
- Controller must not dispatch a write-capable implementer lane to discover an
  unknown product fact. Dispatch bounded read-only research first when source
  can resolve it; otherwise block for a requirements or specification decision.

## Per Task

1. Controller submits typed criteria through current route policy. Core resolves
  a dispatchable request, packet, and host compatibility profile; do not force
  legacy API versions. For plan-linked work it sends `plan_ref` and
  `plan_task_id` only; core derives mode, base, allowed paths, and planned
  paths before enforced host dispatch.
2. Harness authorizes planned protected paths, prepares workspace, dispatches,
   collects claim, snapshots actual changes, and records criterion evidence.
3. Implementer changes only lane paths, runs task-local proof, and reports
   claim, changed files, concerns, and normalized friction.
4. If review is required, controller obtains read-only reviewer evidence. Review
   cannot authorize protected paths; approval cannot prove semantic criteria.
5. Controller records one allowed decision. Retry, escalation, and approval
   create successor attempts only when outcome permits. For `dispatch_timeout`,
   controller may only escalate through packet `escalation_profile` or block;
   never retry timeout. Prior packets and evidence stay unchanged.
   When finalization runs, lane evidence retains bounded prior terminal state
   and read-only finalizer identity. A finalizer claim may be claim-only; it
   does not need a second packet-tool call.
   `recover-stranded` is controller-only non-replay recovery for a leased
   `running` attempt with no claim, node observation, evidence, outcome, or
   decision after host terminal recording failed. It requires exact run/attempt
   identity plus bounded external host evidence with `source: host` and
   `code: terminal_recording_failed`. It creates block-only recovery evidence;
   never use it for product failure or ordinary running work.

## Stop

Stop with managed `block` when host capability is unavailable, lane scope
overlaps another active writer, proof cannot run, or approval gate triggers.
Use explicit `waive` only to record local-only `unvalidated` work. Do not use
manual controller glue to bypass recorded outcome or decision.

For managed terminal failure, return packet evidence only. Core records
friction; controller alone routes recurring candidates to `skill-improve-harness`.
