---
name: skill-dispatching-parallel-agents
description: Use when controller selects isolated parallel lanes with disjoint write ownership.
required_reads: []
distribution_tier: starter_kit
---
# Dispatching Parallel Agents

Use only when controller selects canonical `parallel_work_lanes` in one
resolved harness packet. Do not use legacy aliases in new managed requests or
parallelism to investigate likely shared root cause.

## Preconditions

- Each lane has exact, disjoint `allowed_paths` and one bounded deliverable.
- Every writable lane uses its own isolated workspace or worktree.
- Shared-workspace lanes are read-only only.
- Controller selects only `low`, `normal`, or `high`. Agents may create child
  agents only when immutable packet grants `harness.delegate` and selects
  `read_only_research`; core enforces child authority, paths, depth, budget,
  and read-only workspace. In every other packet, agents must not spawn child
  agents.

## Process

1. Controller resolves one immutable packet with exact lane ownership; host
   preflights packet-selected bindings and isolated workspaces for every lane.
2. Dispatch all independent lanes before waiting.
3. Each agent returns `claimed_result` with changed files, proof, concerns, and
   reusable friction. No agent returns `verified`.
4. Harness materializes lane changes, then runs packet integration, validator,
   and checks in final packet workspace.
5. Controller reconciles verified evidence, resolves conflicts source-first,
   then records final decision.

## Stop

Run sequentially when paths overlap, environment state is shared, order is
uncertain, or any lane needs another lane's result. Controller owns retry,
escalation, approval, and final integration.
