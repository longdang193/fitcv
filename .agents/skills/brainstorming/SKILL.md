---
name: brainstorming
description: "Use when exploring or defining new behavior, features, components, or non-trivial changes before implementation."
---

# Brainstorming Ideas Into Designs

<HARD-GATE>
Do NOT write code or implement anything before:
1. design is presented
2. user explicitly approves
</HARD-GATE>

## Role

This skill produces design artifacts only.

## Canonical References

- `docs/operating_system/templates/task-start-routing-guide.md`
- `docs/operating_system/templates/complete-specification-set-template.md`
- `docs/operating_system/templates/spec-authoring-map-template.md`
- `docs/operating_system/templates/detailed-specification-template.md`
- `docs/operating_system/repo-governance.md`

If this file conflicts with canonical templates/governance, follow canonical docs.

## Mandatory Read

Before any brainstorming output, read:

- `docs/operating_system/templates/task-start-routing-guide.md`

## Minimal Workflow

1. Use `planning-dispatch` triage (or verify it already exists).
2. Explore options and tradeoffs.
3. Recommend a design direction.
4. Author the required spec artifact using canonical templates.
5. Request approval before any implementation planning.

## Output Paths

- specs -> `docs/superpowers/specs/`
- execution maps -> `docs/superpowers/execution_maps/`

## Guardrails

- Keep this skill focused on design decisions.
- Avoid duplicating lifecycle policy text already defined in templates/validators.
