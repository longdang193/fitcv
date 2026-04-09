# Repo Governance

This document defines how the private FitCV repo is organized for humans and agents.

## Repo Roles

- Private repo:
  - full development source of truth
  - internal docs, workflows, specs, plans, and tooling are allowed
- Public repo:
  - curated product-facing mirror
  - receives only intentionally published code and docs

Normal development happens only in the private repo.

## Structure Model

The repo uses five distinct internal layers:

1. `docs/operating_system/`
- human-readable repo rules and workflows
- publication policy
- doc-system and planning rules
- internal tooling pilots
- agent memory under `docs/operating_system/agent_memory/`

2. `agent-core/`
- shared agent-facing source material
- small principles
- structured policy intent
- adapter source files

3. `.agents/skills/`
- repo-local Codex skill discovery surface
- focused task playbooks

4. adapter outputs
- `AGENTS.md`
- nested `AGENTS.md`
- `codex/rules/*.rules`
- sync and verification scripts under `scripts/`

## Ownership Rules

### `docs/operating_system/`

Owns:

- repo operating rules
- workflow governance
- publication workflow
- tool adoption policy
- operational agent memory

Does not own:

- product behavior
- runtime code contracts
- task playbooks

`docs/operating_system/agent_memory/` stores compact operational memory for agents. It does not replace feature docs, specs, plans, or generated rules.

### `agent-core/`

Owns:

- shared agent-facing material that may be rendered into adapter-specific files

Does not own:

- the full human governance layer
- public product docs

### `.agents/skills/`

Owns:

- reusable execution workflows
- the canonical Codex skill discovery surface in phase 2

Does not own:

- publication policy
- repo-wide governance
- adapter syntax

Formal shape is governed by `docs/operating_system/skills-governance.md`.

## Private / Public Boundary

The following are private-only by default:

- `docs/operating_system/`
- `agent-core/`
- `codex/rules/`
- root and nested `AGENTS.md`
- `.agents/`
- `.cursor/`
- `docs/superpowers/`
- `logs/`
- `sample/`

The public repo must not depend on these files to understand or use the product.

## Current Phase

Phase 2 keeps `.agents/skills/` as the canonical skill source.

This avoids breaking current Codex skill discovery while the new `agent-core/` and adapter sync layer stabilizes.

Longer term, `agent-core/skills/` may become canonical, with `.agents/skills/` generated or synchronized from it.

## Adapter Workflow

When changing:

- `agent-core/adapters/*`
- `agent-core/policies/*`
- generated `AGENTS.md`
- generated `codex/rules/*.rules`

run:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
```

## Hook Workflow

The repo hook workflow is part of normal enforcement.

CI is expected to run adapter verification and baseline checks on push and pull request events so drift and broken changes are caught before merge.
