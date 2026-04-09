# Patterns

## Adapter source changes

- Change adapter sources in `agent-core/`, not generated `AGENTS.md` or `codex/rules/*.rules`.
- After adapter-source edits, run sync and verify before calling the work complete.

## Cross-cutting repo work

- If the work changes repo operating behavior rather than a product feature contract, keep docs under `docs/operating_system/` and use `Feature: none`.
- Update only the smallest set of governance docs needed to explain the new operating behavior.

## Spec to plan to execution

- Write the spec first for new cross-cutting repo behavior.
- Turn the approved direction into a concrete implementation plan.
- Execute the plan with verification evidence before claiming completion.
