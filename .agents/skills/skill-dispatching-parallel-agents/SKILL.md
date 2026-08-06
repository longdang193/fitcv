---
name: skill-dispatching-parallel-agents
description: Use when controller selects isolated parallel lanes with disjoint write ownership.
required_reads: []
distribution_tier: starter_kit
---
# Dispatching Parallel Agents

Use only when controller selects `parallel_lanes` in validated harness packets.
Do not use parallelism to investigate likely shared root cause.

## Preconditions

- Each lane has exact, disjoint `allowed_paths` and one bounded deliverable.
- Every writable lane uses its own isolated workspace or worktree.
- Shared-workspace lanes are read-only only.
- Controller selects only `low`, `normal`, or `high`; agents do not spawn
  child agents.

## Process

1. Controller records lane ownership and preflights one packet per lane.
2. Dispatch all independent lanes before waiting.
3. Each agent returns `claimed_result` with changed files, proof, concerns, and
   reusable friction. No agent returns `verified`.
4. Harness verifies each lane against its own packet.
5. Controller reconciles results, resolves conflicts source-first, then runs
   combined verification before acceptance.

## Stop

Run sequentially when paths overlap, environment state is shared, order is
uncertain, or any lane needs another lane's result. Controller owns retry,
escalation, approval, and final integration.
