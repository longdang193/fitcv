# Skills Governance

This document defines how skills are formalized in the private repo.

## Canonical Surface In Phase 2

The canonical Codex skill surface remains:

```text
.agents/skills/
```

This repo does not currently use a hidden `.codex/` directory as the
canonical Codex skill root. The active ownership model is:

- `AGENTS.md` for repo-wide Codex instructions
- `.agents/skills/` for canonical Codex skills
- `.codex/agents/` for optional narrow Codex subagent configuration
- `docs/operating_system/` for human governance
- `.codex/rules/` for generated rules output

Phase 2 does not move canonical skill ownership into `agent-core/skills/`.

That migration stays deferred until the adapter and sync model is more mature.

## Codex Skills Model

This repo follows the Codex Skills model for formal skill shape:

- one skill folder per focused workflow
- `SKILL.md` as the required entrypoint
- optional `scripts/`, `references/`, `assets/`, and `agents/openai.yaml` only when they materially help the workflow
- strong `description` fields so Codex can trigger the right skill reliably

## What Skills Are For

Skills are for:

- reusable execution workflows
- debugging methods
- planning methods
- review workflows
- focused task workflows

Skills are not for:

- repo governance
- publication policy
- broad operating-system rules
- vendor-specific execution-policy syntax

Those belong in:

- `docs/operating_system/`
- `agent-core/policies/`
- `.codex/rules/`

`.codex/rules/` is a generated rules surface. It is not the canonical home for
skills, agent memory, or repo governance.

## Relationship To Subagents

If `.codex/agents/` exists in this repo:

- it is an optional specialist executor layer
- it does not replace `.agents/skills/`
- it must stay narrower and more role-specific than the skill layer
- it must not become a second governance surface

## Quality Rules

Each skill should:

- solve one focused job
- keep `SKILL.md` readable and trigger-oriented
- use helper files only when they add real value
- avoid turning into a general project manual


## Validation Rule

New skills are not considered trustworthy just because they were written down.

Before a new skill is treated as landed:

- validate it with the `writing-skills` workflow
- define a baseline failure scenario
- define the expected post-skill success behavior
- tighten loopholes when the first version still leaves room for bad shortcuts
- capture a short reusable validation summary in
  `docs/operating_system/skills-validation-report.md` when the change affects
  repo-wide routing or governance behavior

In this repo, skill additions should be treated as process TDD rather than
plain documentation edits.
## Migration Rule

If future work introduces `agent-core/skills/`, that layer must not become canonical until:

- sync behavior is defined
- verification proves outputs are trustworthy
- Codex discovery still works cleanly through `.agents/skills/`
