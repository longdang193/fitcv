# Skills Governance

This document defines how skills are formalized in the private repo.

## Canonical Surface In Phase 2

The canonical Codex skill surface remains:

```text
.agents/skills/
```

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
- focused task playbooks

Skills are not for:

- repo governance
- publication policy
- broad operating-system rules
- vendor-specific execution-policy syntax

Those belong in:

- `docs/operating_system/`
- `agent-core/policies/`
- `codex/rules/`

## Quality Rules

Each skill should:

- solve one focused job
- keep `SKILL.md` readable and trigger-oriented
- use helper files only when they add real value
- avoid turning into a general project manual

## Migration Rule

If future work introduces `agent-core/skills/`, that layer must not become canonical until:

- sync behavior is defined
- verification proves outputs are trustworthy
- Codex discovery still works cleanly through `.agents/skills/`
