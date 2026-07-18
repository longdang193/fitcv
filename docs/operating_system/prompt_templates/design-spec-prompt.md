---
name: design-spec-prompt
description: Turn understood problem and repository evidence into approved behavioral and design specification.
distribution_tier: starter_kit
---
# Design Spec Prompt

Start from user need, approved brainstorming direction, or diagnosed root cause. Gather current-state evidence from source, tests, configuration, interfaces, Serena, GitNexus, native tools, or relevant MCPs only as needed.

Define:

- problem, affected actors, evidence, consequence, goal, and observable success
- scope, non-goals, admissible cases, and compatibility expectations
- required outcomes and behavioral contracts
- interfaces, identity, schemas, state transitions, defaults, errors, retries, and boundary conversions when relevant
- design decisions, rationale, alternatives, trade-offs, ownership, invariants, edge cases, migration, and risks
- acceptance criteria and validation intent for every required outcome

Separate verified facts, assumptions, unresolved questions, and design implications. Prefer existing repository and native capabilities. Keep exact files, task order, commands, dependencies, rollout steps, and execution waves in implementation plan.

Write approved result using detailed specification template, request review when risk warrants it, then hand off to `skill-writing-plans` after approval.
