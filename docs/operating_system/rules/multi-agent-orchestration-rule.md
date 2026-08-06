---
name: multi-agent-orchestration
description: Govern controller-owned multi-agent dispatch, write isolation, and independent verification.
alwaysApply: false
required_reads:
- AGENTS.md
tags:
- rule
- agents
- orchestration
distribution_tier: starter_kit
---

# Multi-Agent Orchestration Rule

- Controller alone dispatches, retries, escalates, or requests approval.
- Each lane gets one validated harness packet with exact allowed paths, base
  ref, tools, checks, and approval gates.
- Work without a host-created packet and `run.json` is source-first local work,
  never managed or accepted harness work.
- Agents do not spawn child agents. They return `claimed_result`; harness
  records verification evidence and controller records final decision.
- Missing enforced host capability returns `execution_mode_unavailable` before
  dispatch. Controller either blocks or records `waive` with reason; waiver is
  terminal `unvalidated`, never acceptance.
- Independent validation requires an enforced read-only validator lane and its
  own claim. Implementer claims and local checks never substitute.
- Parallel writers require disjoint allowed paths and isolated workspaces.
- Shared-workspace parallel work is read-only only.
- Commit policy remains external. Per-task commits are never required for
  dispatch or review.
