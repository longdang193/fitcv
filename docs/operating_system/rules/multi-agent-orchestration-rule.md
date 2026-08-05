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
- Agents do not spawn child agents. They return `claimed_result`; harness alone
  returns `verified` evidence.
- Parallel writers require disjoint allowed paths and isolated workspaces.
- Shared-workspace parallel work is read-only only.
- Commit policy remains external. Per-task commits are never required for
  dispatch or review.
