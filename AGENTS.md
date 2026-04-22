# GENERATED FILE - do not edit directly.
# Source: `agent-core/adapters/codex/root-AGENTS.template.md`
# Project Agent Instructions

This file is the repo-wide instruction layer for Codex.

## Scope

Use this file for repo-wide behavior only. More specific directory instructions may override it.

## Repo Rules

- The private repo is the development source of truth.
- The public repo is updated only through the curated publish workflow.
- Repo governance lives in `docs/operating_system/`.
- Agent memory lives in `docs/operating_system/agent_memory/`.
- Skills live in `.agents/skills/`, which remains the canonical Codex skill surface.
- Runtime/workflow config lives in `config/`, while repo/system config lives in `repo_config/`.
- `codex/rules/` is a generated rules output surface, not the canonical home for skills or memory.
- Skills should follow the Codex Skills model: one focused workflow per skill, with `SKILL.md` as the primary entrypoint.

## Working Expectations

- Keep changes aligned with the owning code and doc layer.
- Consult relevant agent memory before planning when the task touches reusable repo workflows or known invariants.
- Consult `docs/operating_system/agent_memory/failure-ledger.md` during debugging, retries, or after important mistakes.
- Update the agent-memory layer when a significant reusable lesson emerges.
- Update tests and docs when behavior or contracts change.
- Do not expose private operating-system or agent-core material through the public mirror.
- If you change `agent-core/adapters/*`, generated `AGENTS.md`, or `codex/rules/*.rules`, run the sync and verify scripts before considering the change complete.

